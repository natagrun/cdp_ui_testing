
import datetime
import json
import os


class StepLogger:
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.steps = []
        self.start_time = datetime.datetime.utcnow().isoformat()
        self.log_file_path = self._generate_log_path()

    def _generate_log_path(self) -> str:
        date_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_name = f"{self.test_name}_{date_str}.json"
        os.makedirs("logs", exist_ok=True)
        return os.path.join("logs", file_name)

    def log_step(self, description: str, success: bool, details: str = ""):
        step = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "description": description,
            "success": success,
            "details": details
        }
        self.steps.append(step)
        self._append_step_to_file(step)

    def _append_step_to_file(self, step: dict):
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            json.dump(step, f, ensure_ascii=False)
            f.write(",\n")

    def finalize(self):
        summary = {
            "test_name": self.test_name,
            "start_time": self.start_time,
            "end_time": datetime.datetime.utcnow().isoformat(),
            "total_steps": len(self.steps),
            "success_count": sum(1 for s in self.steps if s["success"]),
            "fail_count": sum(1 for s in self.steps if not s["success"])
        }
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"summary": summary}, ensure_ascii=False))
