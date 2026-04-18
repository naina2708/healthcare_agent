"""
Healthcare Planning Assistant Agent
LangChain + Groq powered - Real LLM reasoning
"""

import json
import os
import time
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

load_dotenv()

# ─────────────────────────────────────────────
#  LLM SETUP
# ─────────────────────────────────────────────

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama3-8b-8192",
    temperature=0.3,
)

# ─────────────────────────────────────────────
#  MOCK TOOL LAYER
# ─────────────────────────────────────────────

class DoctorAvailabilityAPI:
    DOCTORS = {
        "General Physician": ["Dr. Sharma", "Dr. Mehta"],
        "Cardiologist":      ["Dr. Patel"],
        "Neurologist":       ["Dr. Rao"],
        "Endocrinologist":   ["Dr. Gupta"],
        "Pulmonologist":     ["Dr. Joshi"],
        "Orthopedist":       ["Dr. Verma"],
        "Dermatologist":     ["Dr. Kapoor"],
        "Psychiatrist":      ["Dr. Nair"],
    }

    def check_availability(self, specialty: str) -> dict:
        time.sleep(0.1)
        doctors = self.DOCTORS.get(specialty, [])
        if doctors:
            doctor = random.choice(doctors)
            slot = (datetime.now() + timedelta(hours=random.randint(2, 48))).strftime("%Y-%m-%d %H:%M")
            return {"available": True, "doctor": doctor, "next_slot": slot, "specialty": specialty}
        return {"available": False, "doctor": None, "next_slot": None, "specialty": specialty}


class MedicineDatabaseAPI:
    MEDICINES = {
        "Paracetamol":  {"stock": True,  "alternatives": []},
        "Metformin":    {"stock": True,  "alternatives": ["Glucophage"]},
        "Lisinopril":   {"stock": False, "alternatives": ["Enalapril", "Ramipril"]},
        "Atorvastatin": {"stock": True,  "alternatives": []},
        "Amoxicillin":  {"stock": True,  "alternatives": ["Azithromycin"]},
        "Aspirin":      {"stock": True,  "alternatives": []},
        "Insulin":      {"stock": True,  "alternatives": ["Glargine"]},
        "Salbutamol":   {"stock": False, "alternatives": ["Formoterol"]},
        "Omeprazole":   {"stock": True,  "alternatives": []},
        "Cetirizine":   {"stock": True,  "alternatives": ["Loratadine"]},
    }

    def check_stock(self, medicine: str) -> dict:
        time.sleep(0.1)
        info = self.MEDICINES.get(medicine, {"stock": True, "alternatives": []})
        return {"medicine": medicine, "in_stock": info["stock"], "alternatives": info["alternatives"]}


class LabTestAPI:
    TESTS = {
        "Complete Blood Count":  {"available": True,  "turnaround": "4 hours"},
        "Blood Glucose Fasting": {"available": True,  "turnaround": "2 hours"},
        "HbA1c":                 {"available": True,  "turnaround": "6 hours"},
        "Lipid Profile":         {"available": True,  "turnaround": "4 hours"},
        "ECG":                   {"available": True,  "turnaround": "30 minutes"},
        "Chest X-Ray":           {"available": False, "turnaround": None},
        "MRI Brain":             {"available": True,  "turnaround": "2 days"},
        "Thyroid Profile":       {"available": True,  "turnaround": "6 hours"},
        "Urine Routine":         {"available": True,  "turnaround": "2 hours"},
        "Liver Function Test":   {"available": True,  "turnaround": "5 hours"},
        "Kidney Function Test":  {"available": True,  "turnaround": "5 hours"},
    }

    def check_test_availability(self, test_name: str) -> dict:
        time.sleep(0.1)
        info = self.TESTS.get(test_name, {"available": True, "turnaround": "1 day"})
        return {"test": test_name, "available": info["available"], "turnaround": info["turnaround"]}


class ToolManager:
    def __init__(self):
        self.doctor_api   = DoctorAvailabilityAPI()
        self.medicine_api = MedicineDatabaseAPI()
        self.lab_api      = LabTestAPI()

    def call_tool(self, tool_name: str, params: dict) -> dict:
        if tool_name == "check_doctor":
            return self.doctor_api.check_availability(params.get("specialty", "General Physician"))
        elif tool_name == "check_medicine":
            return self.medicine_api.check_stock(params.get("medicine", ""))
        elif tool_name == "check_lab":
            return self.lab_api.check_test_availability(params.get("test", ""))
        return {"error": f"Unknown tool: {tool_name}"}


# ─────────────────────────────────────────────
#  DATA MODELS
# ─────────────────────────────────────────────

class Task:
    def __init__(self, task_id, description, task_type, resource,
                 dependencies=None, priority=1, estimated_duration="30 min"):
        self.id                 = task_id
        self.description        = description
        self.task_type          = task_type
        self.resource           = resource
        self.dependencies       = dependencies or []
        self.priority           = priority
        self.estimated_duration = estimated_duration
        self.status             = "pending"
        self.validation_result  = None
        self.scheduled_time     = None
        self.notes              = ""

    def to_dict(self):
        return {
            "id":                 self.id,
            "description":        self.description,
            "task_type":          self.task_type,
            "resource":           self.resource,
            "dependencies":       self.dependencies,
            "priority":           self.priority,
            "estimated_duration": self.estimated_duration,
            "status":             self.status,
            "validation_result":  self.validation_result,
            "scheduled_time":     self.scheduled_time,
            "notes":              self.notes,
        }


class ExecutionPlan:
    def __init__(self, goal, tasks, timeline, summary):
        self.goal       = goal
        self.tasks      = tasks
        self.timeline   = timeline
        self.summary    = summary
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return {
            "goal":       self.goal,
            "tasks":      [t.to_dict() for t in self.tasks],
            "timeline":   self.timeline,
            "summary":    self.summary,
            "created_at": self.created_at,
        }


class MemoryStore:
    def __init__(self):
        self._store = []

    def add(self, entry: dict):
        entry["timestamp"] = datetime.now().isoformat()
        self._store.append(entry)

    def get_all(self):
        return self._store


class Scheduler:
    def optimize_tasks(self, tasks):
        task_map = {t.id: t for t in tasks}
        visited, result = set(), []

        def dfs(task_id):
            if task_id in visited:
                return
            visited.add(task_id)
            for dep_id in task_map[task_id].dependencies:
                if dep_id in task_map:
                    dfs(dep_id)
            result.append(task_map[task_id])

        for t in tasks:
            dfs(t.id)

        result.sort(key=lambda x: -x.priority)
        return result

    def generate_timeline(self, tasks):
        timeline, current_time = [], datetime.now()
        for i, task in enumerate(tasks):
            task.scheduled_time = current_time.strftime("%Y-%m-%d %H:%M")
            timeline.append({
                "step":           i + 1,
                "task_id":        task.id,
                "description":    task.description,
                "type":           task.task_type,
                "scheduled_time": task.scheduled_time,
                "duration":       task.estimated_duration,
                "status":         task.status,
            })
            hours = 1 if "min" in task.estimated_duration.lower() else 4
            current_time += timedelta(hours=hours)
        return timeline


# ─────────────────────────────────────────────
#  LANGCHAIN PROMPTS
# ─────────────────────────────────────────────

CONDITION_PROMPT = PromptTemplate(
    input_variables=["goal"],
    template="""
You are a healthcare AI assistant. A user has given this goal:
"{goal}"

Identify the primary medical condition and return a JSON object with:
- "condition": the condition in lowercase (e.g. diabetes, fever, hypertension, cardiac, respiratory)
- "description": a short professional plan title (e.g. "Comprehensive Diabetes Management Plan")

Respond ONLY with valid JSON. No explanation. No markdown. No extra text.
Example: {{"condition": "diabetes", "description": "Comprehensive Diabetes Management Plan"}}
"""
)

TASK_DECOMPOSITION_PROMPT = PromptTemplate(
    input_variables=["goal", "condition"],
    template="""
You are a healthcare planning AI. Generate a structured treatment plan for:
Goal: "{goal}"
Condition: "{condition}"

Return a JSON array of tasks. Each task must have:
- "id": integer starting from 1
- "description": clear task description
- "task_type": one of ["consultation", "lab_test", "medication", "followup"]
- "resource": doctor specialty, medicine name, or lab test name (be specific)
- "dependencies": list of task ids that must complete before this one ([] if none)
- "priority": integer 1-3 (3=high, 2=medium, 1=low)
- "estimated_duration": string like "30 min", "2 hours", "Ongoing", "7 days"

Rules:
- consultation: resource = doctor specialty (e.g. "General Physician", "Cardiologist", "Endocrinologist")
- lab_test: resource = exact test name (e.g. "Complete Blood Count", "ECG", "HbA1c")
- medication: resource = medicine name (e.g. "Metformin", "Aspirin", "Paracetamol")
- followup: resource = doctor specialty
- Generate 5-8 tasks total
- Consultation must come first (no dependencies), tests before medications

Respond ONLY with a valid JSON array. No explanation. No markdown. No extra text.
"""
)


# ─────────────────────────────────────────────
#  PLANNER AGENT
# ─────────────────────────────────────────────

class PlannerAgent:
    def __init__(self):
        self.tool_manager  = ToolManager()
        self.scheduler     = Scheduler()
        self.memory        = MemoryStore()
        self.reasoning_log = []

        self.condition_chain = LLMChain(llm=llm, prompt=CONDITION_PROMPT)
        self.task_chain      = LLMChain(llm=llm, prompt=TASK_DECOMPOSITION_PROMPT)

    def _log(self, msg: str):
        self.reasoning_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def understand_goal(self, goal: str) -> tuple:
        self._log(f"Sending goal to Groq LLM: '{goal}'")
        raw = self.condition_chain.run(goal=goal)
        raw = raw.strip().replace("```json", "").replace("```", "").strip()
        parsed      = json.loads(raw)
        condition   = parsed.get("condition", "general checkup")
        description = parsed.get("description", "Healthcare Plan")
        self._log(f"LLM detected: '{condition}' → {description}")
        self.memory.add({"type": "goal_understood", "condition": condition})
        return condition, description

    def decompose_tasks(self, goal: str, condition: str) -> list:
        self._log("LLM decomposing goal into tasks...")
        raw = self.task_chain.run(goal=goal, condition=condition)
        raw = raw.strip().replace("```json", "").replace("```", "").strip()
        task_data = json.loads(raw)
        tasks = []
        for t in task_data:
            task = Task(
                task_id            = t["id"],
                description        = t["description"],
                task_type          = t["task_type"],
                resource           = t["resource"],
                dependencies       = t.get("dependencies", []),
                priority           = t.get("priority", 2),
                estimated_duration = t.get("estimated_duration", "30 min"),
            )
            tasks.append(task)
            self._log(f"  Task {task.id}: {task.description} [{task.task_type}]")
        self.memory.add({"type": "tasks_decomposed", "count": len(tasks)})
        return tasks

    def validate_resources(self, tasks: list) -> list:
        self._log("Validating resources via mock tool APIs...")
        for task in tasks:
            if task.task_type == "consultation":
                result = self.tool_manager.call_tool("check_doctor", {"specialty": task.resource})
                task.validation_result = result
                if result["available"]:
                    task.status = "validated"
                    task.notes  = f"Assigned to {result['doctor']} | Slot: {result['next_slot']}"
                    self._log(f"  ✓ Task {task.id}: {result['doctor']} available")
                else:
                    task.status = "unavailable"
                    task.notes  = f"No {task.resource} available. Consider teleconsultation."
                    self._log(f"  ✗ Task {task.id}: {task.resource} unavailable")

            elif task.task_type == "lab_test":
                result = self.tool_manager.call_tool("check_lab", {"test": task.resource})
                task.validation_result = result
                if result["available"]:
                    task.status = "validated"
                    task.notes  = f"Turnaround: {result['turnaround']}"
                    self._log(f"  ✓ Task {task.id}: Lab available, TAT={result['turnaround']}")
                else:
                    task.status = "unavailable"
                    task.notes  = "Lab test unavailable. Consider alternate facility."
                    self._log(f"  ✗ Task {task.id}: Lab unavailable")

            elif task.task_type == "medication":
                result = self.tool_manager.call_tool("check_medicine", {"medicine": task.resource})
                task.validation_result = result
                if result["in_stock"]:
                    task.status = "validated"
                    task.notes  = f"{task.resource} in stock."
                    self._log(f"  ✓ Task {task.id}: {task.resource} in stock")
                else:
                    alts = result["alternatives"]
                    task.status = "alternative_found" if alts else "unavailable"
                    task.notes  = (f"Out of stock. Alternatives: {', '.join(alts)}"
                                   if alts else "Out of stock. No alternatives.")
                    self._log(f"  ⚠ Task {task.id}: {task.resource} out of stock")

            elif task.task_type == "followup":
                task.status = "scheduled"
                task.notes  = "Follow-up to be confirmed after primary treatment."
                self._log(f"  ✓ Task {task.id}: Follow-up scheduled")

        self.memory.add({"type": "resources_validated"})
        return tasks

    def schedule_and_optimise(self, tasks: list) -> tuple:
        self._log("Resolving dependencies & optimising task order...")
        ordered  = self.scheduler.optimize_tasks(tasks)
        timeline = self.scheduler.generate_timeline(ordered)
        self._log(f"Timeline generated with {len(timeline)} steps")
        return ordered, timeline

    def build_summary(self, condition: str, tasks: list) -> str:
        nVal = sum(1 for t in tasks if t.status == "validated")
        nUna = sum(1 for t in tasks if t.status == "unavailable")
        nAlt = sum(1 for t in tasks if t.status == "alternative_found")
        return (
            f"Healthcare plan for '{condition}' with {len(tasks)} tasks — "
            f"{nVal} validated, {nUna} unavailable, {nAlt} with alternatives."
        )

    def create_plan(self, goal: str) -> dict:
        self.reasoning_log = []
        self._log("=== Planner Agent Started (Groq LLM + LangChain) ===")

        condition, description = self.understand_goal(goal)
        tasks                  = self.decompose_tasks(goal, condition)
        tasks                  = self.validate_resources(tasks)
        ordered, timeline      = self.schedule_and_optimise(tasks)
        summary                = self.build_summary(condition, ordered)

        plan = ExecutionPlan(goal=goal, tasks=ordered, timeline=timeline, summary=summary)
        self._log("=== Plan Complete ===")

        return {
            "plan":          plan.to_dict(),
            "reasoning_log": self.reasoning_log,
            "condition":     condition,
            "description":   description,
        }


if __name__ == "__main__":
    agent  = PlannerAgent()
    result = agent.create_plan("Treatment plan for diabetes management")
    print(json.dumps(result, indent=2))
