
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

import pandas as pd
import streamlit as st

SUBMISSIONS_CSV = Path("inventor_readiness_submissions.csv")
ROADMAP_JSONL = Path("inventor_readiness_roadmaps.jsonl")

st.set_page_config(
    page_title="InventorPath.ai - Invention Readiness Score",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("InventorPath.ai — Invention Readiness Score™")
st.write(
    "Turn an idea into a clearer invention path. Enter your invention details, "
    "then get a readiness score, strengths, weaknesses, and next-step roadmap."
)

st.divider()
st.subheader("Inventor Profile")

col1, col2, col3 = st.columns(3)

with col1:
    inventor_name = st.text_input("Inventor name")
    email = st.text_input("Email (optional)")

with col2:
    invention_name = st.text_input("Invention name")
    stage = st.selectbox(
        "Current stage",
        [
            "Idea only",
            "Sketch / notes",
            "Rough prototype",
            "Working prototype",
            "Tested prototype",
            "Ready for patent / market",
        ],
    )

with col3:
    goal = st.selectbox(
        "Main goal",
        [
            "Understand if idea is worth pursuing",
            "Build a prototype",
            "File a patent",
            "License the idea",
            "Start a business",
            "Find investors or partners",
        ],
    )

st.subheader("Invention Details")

problem = st.text_area("1. What problem does your invention solve?", height=100)
target_user = st.text_area("2. Who has this problem?", height=80)
solution = st.text_area("3. What is your proposed solution?", height=100)
existing_alternatives = st.text_area("4. What do people use now instead?", height=80)
unique_advantage = st.text_area("5. What makes your invention different or better?", height=80)

st.subheader("Readiness Questions")

qcol1, qcol2 = st.columns(2)

with qcol1:
    prototype_status = st.selectbox(
        "Prototype status",
        ["No prototype", "Sketch only", "Rough prototype", "Working prototype", "Tested prototype"],
    )
    customer_validation = st.selectbox(
        "Have you asked potential users if they want this?",
        ["No", "Talked to 1-5 people", "Talked to 6-20 people", "Surveyed/tested with 20+ people"],
    )
    prior_art_search = st.selectbox(
        "Have you searched for similar patents/products?",
        ["No", "Basic Google search", "Product search", "Patent search", "Patent attorney/search professional"],
    )

with qcol2:
    market_clarity = st.selectbox(
        "How clear is the target market?",
        ["Unclear", "Somewhat clear", "Clear niche", "Very clear buyer/customer"],
    )
    manufacturability = st.selectbox(
        "How buildable is the product?",
        ["Unknown", "Maybe possible", "Technically feasible", "Already built/tested"],
    )
    business_model = st.selectbox(
        "How would this make money?",
        ["Unknown", "Sell product", "License patent", "Subscription/service", "B2B sales", "Not sure yet"],
    )

notes = st.text_area("Additional notes", height=80)


def score_invention():
    scores = {}

    problem_points = 0
    if len(problem.strip()) > 30:
        problem_points += 8
    if len(target_user.strip()) > 20:
        problem_points += 6
    if len(existing_alternatives.strip()) > 20:
        problem_points += 6
    scores["Problem Clarity"] = min(problem_points, 20)

    solution_points = 0
    if len(solution.strip()) > 40:
        solution_points += 8
    if len(unique_advantage.strip()) > 30:
        solution_points += 7
    solution_points += {
        "No prototype": 0,
        "Sketch only": 2,
        "Rough prototype": 4,
        "Working prototype": 7,
        "Tested prototype": 10,
    }[prototype_status]
    scores["Solution Quality"] = min(solution_points, 20)

    market_points = {
        "Unclear": 0,
        "Somewhat clear": 5,
        "Clear niche": 8,
        "Very clear buyer/customer": 10,
    }[market_clarity]
    market_points += {
        "No": 0,
        "Talked to 1-5 people": 3,
        "Talked to 6-20 people": 6,
        "Surveyed/tested with 20+ people": 10,
    }[customer_validation]
    scores["Market Need"] = min(market_points, 20)

    defensibility_points = {
        "No": 0,
        "Basic Google search": 4,
        "Product search": 6,
        "Patent search": 10,
        "Patent attorney/search professional": 14,
    }[prior_art_search]
    if len(unique_advantage.strip()) > 30:
        defensibility_points += 6
    scores["Defensibility"] = min(defensibility_points, 20)

    execution_points = {
        "Unknown": 0,
        "Maybe possible": 4,
        "Technically feasible": 8,
        "Already built/tested": 10,
    }[manufacturability]
    execution_points += {
        "Unknown": 0,
        "Not sure yet": 1,
        "Sell product": 5,
        "License patent": 5,
        "Subscription/service": 5,
        "B2B sales": 5,
    }[business_model]
    if stage in ["Working prototype", "Tested prototype", "Ready for patent / market"]:
        execution_points += 5
    scores["Execution Readiness"] = min(execution_points, 20)

    return sum(scores.values()), scores


def score_band(score):
    if score >= 85:
        return "High readiness"
    if score >= 70:
        return "Strong potential"
    if score >= 50:
        return "Promising but needs work"
    if score >= 30:
        return "Early stage"
    return "Needs major clarification"


def generate_strengths(section_scores):
    strengths = []
    for section, points in section_scores.items():
        if points >= 15:
            strengths.append(f"{section}: strong foundation.")
    if not strengths:
        strengths.append("You have an invention idea worth organizing, but it needs more detail before major spending.")
    return strengths


def generate_weaknesses(section_scores):
    weaknesses = []
    for section, points in section_scores.items():
        if points < 10:
            weaknesses.append(f"{section}: needs more work.")
    if not weaknesses:
        weaknesses.append("No major weak area detected, but professional patent and market review are still recommended.")
    return weaknesses


def generate_roadmap(section_scores):
    roadmap = []
    if section_scores["Problem Clarity"] < 15:
        roadmap.append("Clarify the problem, target user, and existing alternatives in one page.")
    if section_scores["Market Need"] < 15:
        roadmap.append("Interview 10-20 potential users and ask how they currently solve this problem.")
    if section_scores["Solution Quality"] < 15:
        roadmap.append("Create sketches, a mockup, or a rough prototype to make the invention easier to evaluate.")
    if section_scores["Defensibility"] < 15:
        roadmap.append("Do a product search and basic patent search before spending heavily on development.")
    if section_scores["Execution Readiness"] < 15:
        roadmap.append("Identify how this will be manufactured, licensed, sold, or partnered.")
    roadmap.append("Create a short invention brief: problem, solution, user, advantage, prototype status, and next action.")
    roadmap.append("When ready, speak with a patent professional before publicly disclosing sensitive details.")
    return roadmap


def save_submission(score, section_scores, band, strengths, weaknesses, roadmap):
    submission_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "Submission ID": submission_id,
        "Saved At UTC": now,
        "Inventor Name": inventor_name,
        "Email": email,
        "Invention Name": invention_name,
        "Goal": goal,
        "Stage": stage,
        "Score": score,
        "Band": band,
        "Problem": problem,
        "Target User": target_user,
        "Solution": solution,
        "Existing Alternatives": existing_alternatives,
        "Unique Advantage": unique_advantage,
        "Prototype Status": prototype_status,
        "Customer Validation": customer_validation,
        "Prior Art Search": prior_art_search,
        "Market Clarity": market_clarity,
        "Manufacturability": manufacturability,
        "Business Model": business_model,
        "Notes": notes,
    }

    df = pd.DataFrame([record])
    if SUBMISSIONS_CSV.exists():
        old = pd.read_csv(SUBMISSIONS_CSV).fillna("")
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(SUBMISSIONS_CSV, index=False)

    json_record = {
        "submission_id": submission_id,
        "saved_at_utc": now,
        "source": "inventorpath_readiness_score_app",
        "invention": {
            "name": invention_name,
            "goal": goal,
            "stage": stage,
            "problem": problem,
            "target_user": target_user,
            "solution": solution,
            "existing_alternatives": existing_alternatives,
            "unique_advantage": unique_advantage,
        },
        "assessment_inputs": {
            "prototype_status": prototype_status,
            "customer_validation": customer_validation,
            "prior_art_search": prior_art_search,
            "market_clarity": market_clarity,
            "manufacturability": manufacturability,
            "business_model": business_model,
            "notes": notes,
        },
        "readiness_score": {
            "overall_score": score,
            "band": band,
            "section_scores": section_scores,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "roadmap": roadmap,
        },
        "inventorpath_next_step": roadmap[0] if roadmap else "Clarify next step.",
    }

    with ROADMAP_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(json_record, ensure_ascii=False) + "\n")


if st.button("Calculate Invention Readiness Score"):
    score, section_scores = score_invention()
    band = score_band(score)
    strengths = generate_strengths(section_scores)
    weaknesses = generate_weaknesses(section_scores)
    roadmap = generate_roadmap(section_scores)

    st.divider()
    st.header(f"Score: {score}/100 — {band}")

    st.subheader("Section Scores")
    score_df = pd.DataFrame([{"Category": k, "Score": v, "Max": 20} for k, v in section_scores.items()])
    st.dataframe(score_df, width="stretch", hide_index=True)

    st.subheader("Strengths")
    for item in strengths:
        st.success(item)

    st.subheader("Weaknesses")
    for item in weaknesses:
        st.warning(item)

    st.subheader("Recommended Next Steps")
    for i, step in enumerate(roadmap, start=1):
        st.write(f"{i}. {step}")

    save_submission(score, section_scores, band, strengths, weaknesses, roadmap)
    st.info(f"Saved assessment to {SUBMISSIONS_CSV} and {ROADMAP_JSONL}.")

st.divider()
st.caption(
    "Disclaimer: This is an educational readiness tool, not legal, patent, financial, or business advice. "
    "Consult a qualified patent attorney or business professional before making major decisions."
)
