# Live Demonstration Guide — Pharmacy Substitution Decision Support System

This script provides a 5–10 minute step-by-step demonstration sequence with talking points for evaluators and viva examiners.

---

## Demo Overview (5–10 Minutes)

| Step | Time | View / Screen | Scenario / Action | Key Talking Point |
| --- | --- | --- | --- | --- |
| **1** | 0:30 | Main Header | Check Database Badge | "System connects live to PostgreSQL with real-time health checks (`GET /ready`)." |
| **2** | 1:00 | Dashboard | Review KPI Overview | "Real-time decision distribution, risk levels, and safety block breakdowns." |
| **3** | 2:00 | Evaluate | Preset `PAT-0001` (Safe) | "100% deterministic safety pipeline evaluating 9 clinical rules in strict sequence." |
| **4** | 3:30 | Evaluate | Preset `PAT-0002` (Allergy Block) | "Patient with severe Penicillin allergy triggers instant FAIL on check #2 with evidence." |
| **5** | 4:30 | Evaluate | Preset `PAT-0003` (Pregnancy) | "Teratogenic drug contraindication automatically blocked for active pregnancy." |
| **6** | 5:30 | Evaluate | Preset `PAT-0005` (Stock Block) | "Zero usable unexpired stock in physical inventory causes immediate stock block." |
| **7** | 7:00 | Decision Details | Open Decision & Review | "Human-in-the-loop governance: Pharmacists can Approve, Reject, or Override." |
| **8** | 8:30 | Review Modal | Test Override Validation | "Client & backend validate that clinical overrides require non-empty override_reason." |
| **9** | 9:30 | Governance & Audit | History / Fairness / Error | "Complete compliance audit trails and synthetic demographic cohort fairness metrics." |

---

## Step-by-Step Script & Talking Points

### Step 1: System Identification & Database Health (0:00 - 0:30)
- **Action**: Open [http://localhost:5173](http://localhost:5173). Point to the top header banner.
- **Talking Point**:
  > "Welcome to the Pharmacy Substitution Decision Support System. Notice in the top right header that the database status badge shows 'PostgreSQL Connected'. The application polls the backend `GET /ready` endpoint, which executes an active SQL query against our PostgreSQL database `pharmacy_substitution_db`."

---

### Step 2: System Dashboard Overview (0:30 - 1:30)
- **Action**: Click the **Dashboard** navigation tab.
- **Talking Point**:
  > "The Dashboard presents aggregated decision support metrics. We see total evaluated decisions, recommended count, safety blocked count, and pharmacist review statuses. Below, risk level distributions are categorized into LOW, MEDIUM, HIGH, and CRITICAL, alongside safety block counts across allergy, renal, hepatic, pregnancy, age, interaction, dosage, and stock categories."

---

### Step 3: Scenario A — Safe Substitution (`PAT-0001`) (1:30 - 3:00)
- **Action**: Click **Evaluate Request**. Click the quick test preset button **`Safe Substitution (PAT-0001)`**. Click **Run Safety Evaluation**.
- **Talking Point**:
  > "Here we evaluate Patient PAT-0001 prescribed Lisinopril 10mg. The system executes our deterministic 9-check safety engine in strict sequential order: approved alternative lookup, allergy contraindications, renal limits, hepatic limits, pregnancy, age boundaries, drug interactions, dosage limits, and stock availability. All 9 checks pass, and the system selects the single best candidate using our 5-tier priority ranking algorithm. Notice that 'Requires Human Confirmation' is set to YES."

---

### Step 4: Scenario B — Allergy Block (`PAT-0002`) (3:00 - 4:30)
- **Action**: Click **`Severe Allergy Block (PAT-0002)`** preset button. Click **Run Safety Evaluation**.
- **Talking Point**:
  > "Now we evaluate PAT-0002 prescribed Amoxicillin 500mg. The system evaluates the candidate alternatives and triggers an immediate FAIL on Check #2: Patient Allergy Contraindication. Because PAT-0002 has a recorded severe Penicillin allergy, the alternative is marked UNSAFE and blocked. Notice the recommended_medicine is NULL, the decision status is BLOCKED, the risk level is CRITICAL, and the clinical evidence box details the exact allergy record."

---

### Step 5: Scenario C — Pregnancy Contraindication Block (`PAT-0003`) (4:30 - 5:30)
- **Action**: Click **`Pregnancy Block (PAT-0003)`** preset. Click **Run Safety Evaluation**.
- **Talking Point**:
  > "For pregnant patient PAT-0003 requesting Valsartan 80mg, the engine evaluates Check #5: Pregnancy Contraindication. Because Angiotensin Receptor Blockers are contraindicated in pregnancy due to fetal toxicity, the pregnancy check fails with a CRITICAL risk level and blocks the substitution."

---

### Step 6: Scenario D — Physical Inventory Stock Block (`PAT-0005`) (5:30 - 6:30)
- **Action**: Click **`Stock Depletion Block (PAT-0005)`** preset. Click **Run Safety Evaluation**.
- **Talking Point**:
  > "For PAT-0005 requesting Gliclazide 80mg, all clinical checks pass, but Check #9: Usable Stock Availability fails because physical stock in pharmacy inventory is zero. This prevents pharmacists from dispensing out-of-stock medications."

---

### Step 7: Human-in-the-Loop Pharmacist Review & Override (6:30 - 8:30)
- **Action**: Navigate to **Decision History** -> Click **View Details** on decision record #1 -> Click **+ Submit Pharmacist Review**.
- **Action**: Select **OVERRIDDEN** -> Leave override reason blank -> Click Submit (observe client error). Type reason: *"Specialist desensitization authorization attached."* -> Click Submit.
- **Talking Point**:
  > "Human-in-the-loop governance is strictly enforced. Licensed pharmacists can Approve, Reject, or Override decisions using their authorization token. If a pharmacist attempts to override a safety block without providing a reason, submission is blocked. When a valid override reason is submitted, the status updates to OVERRIDDEN, and an immutable `AuditLog` entry is appended in PostgreSQL using pessimistic row locking."

---

### Step 8: Governance Analytics & Demographic Fairness (8:30 - 10:00)
- **Action**: Click **Demographic Fairness** tab -> Click **Safety & Error Audit** tab.
- **Talking Point**:
  > "Finally, our Governance Analytics screens track demographic cohort fairness across Age, Gender, and Organ Impairment groups to monitor potential disparities. All fairness screens prominently display our synthetic population audit disclaimer."
