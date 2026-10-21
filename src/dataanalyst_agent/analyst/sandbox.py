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
        self.client = docker.from_env()


    async def run_code_in_sandbox(self, code: str, timeout: int = 30) -> dict:
        """
        Run Python code safely in a Docker container.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds

        Returns:
            dict with stdout, stderr, and exit code
        """

        # connection python-> docker
        client = docker.from_env()

        tmp_dir = tempfile.mkdtemp()

        code_file = Path(tmp_dir) / "script.py"

        with open(code_file, "w") as f:
            f.write(code)

        container = None
        try:

            container = self.client.containers.run(
                image=self.image,
                working_dir="/sandbox",
                volumes={str(code_file.parent): {"bind": "/sandbox", "mode": "ro"}},
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
                "exit_code": exit_code,            }


        except requests.exceptions.ReadTimeout:
            if container is not None:
                container.kill()
            return {"error": f"Execution exceeded {timeout}s and was killed."}
        
        except Exception as e:
            return {"error": str(e)}
        
        finally:
                if container:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass
                shutil.rmtree(tmp_dir, ignore_errors=True)

  