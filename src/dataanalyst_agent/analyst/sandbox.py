import docker
import tempfile
from pathlib import Path
import shutil
import requests  


class SandBox:
    """sandbox env for running code"""
    def __init__(
        self,image: str = "sandbox:latest",mem_limit: str = "512m",pids_limit: int = 50,tmpfs_size: str = "64m"):

        self.image = image
        self.mem_limit = mem_limit
        self.pids_limit = pids_limit
        self.tmpfs_size = tmpfs_size
        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception:
            raise ConnectionError("Docker is not running. Please start Docker Desktop before running the pipeline.")


    def run_code_in_sandbox(self, code: str,footer:str, csv_path: str = None, timeout: int = 30) -> dict:
        """
        Run Python code safely in a Docker container.

        Args:
            code: Python code to execute
            csv_path: Path to dataset CSV file to mount at /data/data.csv
            timeout: Maximum execution time in seconds

        Returns:
            dict with stdout, stderr, and exit code
        """
        if not csv_path or not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV dataset file not found: {csv_path}")

        tmp_dir = tempfile.mkdtemp()
        code_file = Path(tmp_dir) / "script.py"

        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code + "\n" + footer)

        volumes = {
            str(code_file.parent): {"bind": "/sandbox", "mode": "ro"},
            str(Path(csv_path).resolve()): {"bind": "/data/data.csv", "mode": "ro"},
        }

        container = None
        try:
            container = self.client.containers.run(
                image=self.image,
                working_dir="/sandbox",
                volumes=volumes,
                command=["python", "/sandbox/script.py"],
                detach=True,
                mem_limit=self.mem_limit,
                memswap_limit=self.mem_limit,

                # security measure
                network_disabled=True,
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],
                read_only=True,
                pids_limit=self.pids_limit,
                tmpfs={"/tmp": f"size={self.tmpfs_size}"},
                environment={"MPLCONFIGDIR": "/tmp"},
            )

            # wait(timeout=...) only abandons our wait; it does NOT stop the
            # container. On expiry docker-py raises requests.exceptions.ReadTimeout,
            # so we catch it and kill the still-running container ourselves.
            result = container.wait(timeout=timeout)
            output = container.logs().decode("utf-8")
            exit_code = result["StatusCode"]

            return {
                "stdout": output if exit_code == 0 else "",
                "stderr": "" if exit_code == 0 else output,
                "exit_code": exit_code,
            }

        except requests.exceptions.ReadTimeout:
            if container is not None:
                try:
                    container.kill()
                except Exception:
                    pass
            return {
                "stdout": "",
                "stderr": f"Execution exceeded {timeout}s and was killed.",
                "exit_code": 124,
            }

        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
            }

        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            shutil.rmtree(tmp_dir, ignore_errors=True)

  