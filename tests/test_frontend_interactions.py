from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


class FrontendInteractionSmokeTests(unittest.TestCase):
    def test_frontend_minimal_interactions(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        runner = repo_root / "tests" / "frontend_interaction_runner.js"
        command = (
            "const fs=require('fs');"
            "const path=require('path');"
            f"const filename={runner.resolve().as_posix()!r};"
            "const dirname=path.dirname(filename);"
            "const source=fs.readFileSync(filename,'utf8');"
            "const run=new Function('require','__dirname','__filename', source);"
            "run(require, dirname, filename);"
        )

        result = subprocess.run(
            ["node", "-e", command],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            self.fail(
                "frontend interaction runner failed\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
