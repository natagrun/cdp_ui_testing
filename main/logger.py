import datetime
import json
import os

class StepLogger:
    def __init__(self, name: str):
        self.name = name
        self.steps = []
        self.start_time = datetime.datetime.utcnow().isoformat()

    def log_step(self, description: str, success: bool, error: str = ""):
        self.steps.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "description": description,
            "success": success,
            "error": error
        })

    def generate_report(self) -> dict:
        return {
            "test_name": self.name,
            "start_time": self.start_time,
            "end_time": datetime.datetime.utcnow().isoformat(),
            "steps": self.steps,
            "summary": {
                "total": len(self.steps),
                "passed": len([s for s in self.steps if s['success']]),
                "failed": len([s for s in self.steps if not s['success']])
            }
        }

    def save_to_file(self, path: str) -> str:
        report = self.generate_report()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return path
