
from datetime import datetime, timezone
from pathlib import Path
import json
import smtplib
import uuid
from email.message import EmailMessage
from urllib.parse import quote_plus
import sqlite3

import pandas as pd
import streamlit as st

SUBMISSIONS_CSV = Path("inventor_readiness_submissions.csv")
ROADMAP_JSONL = Path("inventor_readiness_roadmaps.jsonl")
DB_PATH = Path("inventor_readiness_submissions.db")

st.set_page_config(
    page_title="InventorPath.ai - Invention Readiness Score",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("InventorPath.ai")
st.sidebar.markdown(
    "### Use the free invention readiness quiz\n\n"
    "Quickly assess your invention idea from 0 to 100 using local Python logic only. "
    "No paid APIs are required."
)
st.sidebar.markdown(
    "### Upgrade paths\n"
    "- **Free Tier**: Score your idea and get next steps\n"
    "- **Guided Builder**: Build with a structured invention path\n"
    "- **Professional Review**: Expert feedback on your concept\n"
    "- **Attorney Partner Review**: Patent-ready review support\n"
)
st.sidebar.info(
    "Save your score, view strengths and weaknesses, and continue building with InventorPath.ai."
)
st.sidebar.caption(
    "Answer the quiz honestly for the most useful guidance and recommended next steps."
)

st.title("InventorPath.ai — Free Invention Readiness Quiz")
st.markdown(
    "### Score your invention idea from Raw Idea to Investor/Patent Review Ready."
)
st.write(
    "This local, free quiz evaluates your invention on problem validation, market demand, prototype readiness, "
    "patent readiness, and commercialization preparedness."
)
st.write(
    "Submit your answers below to get a 0–100 readiness score, strengths, weaknesses, next steps, and Inventor Academy lesson recommendations."
)


# Top-right data access button
if "show_data_pw" not in st.session_state:
    st.session_state["show_data_pw"] = False

col_l, col_r = st.columns([5, 1])
with col_r:
    if st.button("Data", key="view_data_btn"):
        st.session_state["show_data_pw"] = True

if st.session_state.get("show_data_pw"):
    pw = st.text_input("Enter admin password to view database", type="password", key="admin_pw")
    if pw:
        if pw == "founder1":
            try:
                conn = sqlite3.connect(DB_PATH)
                df_db = pd.read_sql_query("SELECT * FROM submissions ORDER BY saved_at_utc DESC", conn)
                conn.close()
                st.subheader("Submissions Database")
                st.dataframe(df_db)
            except Exception as e:
                st.error(f"Failed to read database: {e}")
        else:
            st.error("Invalid password")

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

    problem_validation_points = 0
    if len(problem.strip()) > 30:
        problem_validation_points += 6
    if len(target_user.strip()) > 20:
        problem_validation_points += 5
    if len(existing_alternatives.strip()) > 20:
        problem_validation_points += 4
    problem_validation_points += {
        "No": 0,
        "Talked to 1-5 people": 3,
        "Talked to 6-20 people": 6,
        "Surveyed/tested with 20+ people": 10,
    }[customer_validation]
    scores["Problem Validation"] = min(problem_validation_points, 20)

    market_demand_points = 0
    market_demand_points += {
        "Unclear": 0,
        "Somewhat clear": 5,
        "Clear niche": 8,
        "Very clear buyer/customer": 10,
    }[market_clarity]
    market_demand_points += {
        "Unknown": 0,
        "Not sure yet": 1,
        "Sell product": 5,
        "License patent": 5,
        "Subscription/service": 6,
        "B2B sales": 7,
    }[business_model]
    market_demand_points += 3 if len(problem.strip()) > 30 else 0
    scores["Market Demand"] = min(market_demand_points, 20)

    prototype_readiness_points = {
        "No prototype": 0,
        "Sketch only": 4,
        "Rough prototype": 8,
        "Working prototype": 12,
        "Tested prototype": 16,
    }[prototype_status]
    prototype_readiness_points += {
        "Unknown": 0,
        "Maybe possible": 3,
        "Technically feasible": 6,
        "Already built/tested": 8,
    }[manufacturability]
    prototype_readiness_points += 1 if stage in ["Rough prototype", "Working prototype", "Tested prototype", "Ready for patent / market"] else 0
    scores["Prototype Readiness"] = min(prototype_readiness_points, 20)

    patent_readiness_points = {
        "No": 0,
        "Basic Google search": 4,
        "Product search": 7,
        "Patent search": 12,
        "Patent attorney/search professional": 16,
    }[prior_art_search]
    if len(unique_advantage.strip()) > 30:
        patent_readiness_points += 4
    if stage in ["Ready for patent / market", "Tested prototype"]:
        patent_readiness_points += 2
    scores["Patent Readiness"] = min(patent_readiness_points, 20)

    commercialization_readiness_points = {
        "Unknown": 0,
        "Not sure yet": 1,
        "Sell product": 6,
        "License patent": 6,
        "Subscription/service": 7,
        "B2B sales": 8,
    }[business_model]
    commercialization_readiness_points += {
        "Unclear": 0,
        "Somewhat clear": 3,
        "Clear niche": 5,
        "Very clear buyer/customer": 7,
    }[market_clarity]
    commercialization_readiness_points += {
        "Unknown": 0,
        "Maybe possible": 2,
        "Technically feasible": 3,
        "Already built/tested": 4,
    }[manufacturability]
    scores["Commercialization Readiness"] = min(commercialization_readiness_points, 20)

    overall_score = sum(scores.values())
    return overall_score, scores


def score_band(score):
    if score >= 76:
        return "Investor/Patent Review Ready"
    if score >= 51:
        return "Development Ready"
    if score >= 26:
        return "Early Concept"
    return "Raw Idea"


def generate_academy_lessons(section_scores):
    lessons = []
    if section_scores["Problem Validation"] < 15:
        lessons.append("Inventor Academy: Validate the problem and target customer")
    if section_scores["Market Demand"] < 15:
        lessons.append("Inventor Academy: Market demand and customer discovery")
    if section_scores["Prototype Readiness"] < 15:
        lessons.append("Inventor Academy: Rapid prototyping and testing")
    if section_scores["Patent Readiness"] < 15:
        lessons.append("Inventor Academy: Patent search and IP positioning")
    if section_scores["Commercialization Readiness"] < 15:
        lessons.append("Inventor Academy: Commercialization strategy and business model")
    if not lessons:
        lessons.append("Inventor Academy: Pitch, review, and prepare for investor / patent meetings")
    return lessons


def generate_strengths(section_scores):
    strengths = []
    for section, points in section_scores.items():
        if points >= 15:
            strengths.append(f"{section}: strong foundation.")
    if not strengths:
        strengths.append(
            "Your idea is worth exploring, and a clearer roadmap will help you move from concepts to a defensible invention."
        )
    return strengths


def generate_weaknesses(section_scores):
    weaknesses = []
    for section, points in section_scores.items():
        if points < 10:
            weaknesses.append(
                f"{section}: needs more detail, validation, or execution planning before advancing."
            )
    if not weaknesses:
        weaknesses.append(
            "No major weak area detected, but professional review is still recommended for patent and commercialization planning."
        )
    return weaknesses


def generate_roadmap(section_scores):
    roadmap = []
    if section_scores["Problem Validation"] < 15:
        roadmap.append(
            "Document the problem, who experiences it, and the current alternatives so you can validate market demand."
        )
    if section_scores["Market Demand"] < 15:
        roadmap.append(
            "Interview 10–20 potential customers and test whether they would pay for your solution."
        )
    if section_scores["Prototype Readiness"] < 15:
        roadmap.append(
            "Build a sketch, prototype, or proof of concept to test assumptions and improve technical confidence."
        )
    if section_scores["Patent Readiness"] < 15:
        roadmap.append(
            "Do a focused patent search and refine your unique advantage before filing or publicly sharing the idea."
        )
    if section_scores["Commercialization Readiness"] < 15:
        roadmap.append(
            "Clarify the business model, revenue path, and production or licensing strategy."
        )
    if not roadmap:
        roadmap.append(
            "Refine your invention brief and then validate with experts in patent, market, and manufacturing."
        )
    roadmap.append(
        "Create a short invention brief: problem, solution, user, advantage, prototype status, and next action."
    )
    roadmap.append(
        "When ready, speak with a patent professional before publicly disclosing sensitive details."
    )
    return roadmap


def academy_link_for(step_text: str) -> str:
    base = "https://inventorpath.ai/academy/search?q="
    return base + quote_plus(step_text)


# Custom target URLs for known roadmap steps
ACADEMY_ROADMAP_LINKS = {
    "Document the problem, who experiences it, and the current alternatives so you can validate market demand.":
        "https://inventorpath.ai/academy/problem-validation",
    "Interview 10–20 potential customers and test whether they would pay for your solution.":
        "https://inventorpath.ai/academy/customer-discovery",
    "Build a sketch, prototype, or proof of concept to test assumptions and improve technical confidence.":
        "https://inventorpath.ai/academy/prototyping",
    "Do a focused patent search and refine your unique advantage before filing or publicly sharing the idea.":
        "https://inventorpath.ai/academy/patent-search",
    "Clarify the business model, revenue path, and production or licensing strategy.":
        "https://inventorpath.ai/academy/commercialization",
    "Refine your invention brief and then validate with experts in patent, market, and manufacturing.":
        "https://inventorpath.ai/academy/expert-review",
    "Create a short invention brief: problem, solution, user, advantage, prototype status, and next action.":
        "https://inventorpath.ai/academy/invention-brief",
    "When ready, speak with a patent professional before publicly disclosing sensitive details.":
        "https://inventorpath.ai/academy/patent-professional",
}

# Custom target URLs for known recommended lessons
ACADEMY_LESSON_LINKS = {
    "Inventor Academy: Validate the problem and target customer":
        "https://inventorpath.ai/academy/validate-problem",
    "Inventor Academy: Market demand and customer discovery":
        "https://inventorpath.ai/academy/market-demand",
    "Inventor Academy: Rapid prototyping and testing":
        "https://inventorpath.ai/academy/prototyping",
    "Inventor Academy: Patent search and IP positioning":
        "https://inventorpath.ai/academy/patent-search",
    "Inventor Academy: Commercialization strategy and business model":
        "https://inventorpath.ai/academy/commercialization",
    "Inventor Academy: Pitch, review, and prepare for investor / patent meetings":
        "https://inventorpath.ai/academy/pitch-review",
}


def get_academy_url_for(text: str) -> str:
    # Exact-match mappings first
    if text in ACADEMY_ROADMAP_LINKS:
        return ACADEMY_ROADMAP_LINKS[text]
    if text in ACADEMY_LESSON_LINKS:
        return ACADEMY_LESSON_LINKS[text]
    # Fallback to search
    return academy_link_for(text)


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


def init_db():
    """Ensure the SQLite DB and submissions table exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id TEXT PRIMARY KEY,
                saved_at_utc TEXT,
                inventor_name TEXT,
                email TEXT,
                invention_name TEXT,
                goal TEXT,
                stage TEXT,
                score INTEGER,
                band TEXT,
                problem TEXT,
                target_user TEXT,
                solution TEXT,
                existing_alternatives TEXT,
                unique_advantage TEXT,
                prototype_status TEXT,
                customer_validation TEXT,
                prior_art_search TEXT,
                market_clarity TEXT,
                manufacturability TEXT,
                business_model TEXT,
                notes TEXT
            )
            """,
        )
        conn.commit()
        conn.close()
    except Exception:
        # If DB cannot be initialized, allow the app to continue using CSV/JSONL
        pass
    # Also insert into SQLite DB for structured queries and UI display
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            INSERT OR REPLACE INTO submissions (
                submission_id, saved_at_utc, inventor_name, email, invention_name,
                goal, stage, score, band, problem, target_user, solution,
                existing_alternatives, unique_advantage, prototype_status,
                customer_validation, prior_art_search, market_clarity,
                manufacturability, business_model, notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                submission_id,
                now,
                inventor_name,
                email,
                invention_name,
                goal,
                stage,
                score,
                band,
                problem,
                target_user,
                solution,
                existing_alternatives,
                unique_advantage,
                prototype_status,
                customer_validation,
                prior_art_search,
                market_clarity,
                manufacturability,
                business_model,
                notes,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        # Do not block main flow if DB write fails; CSV/JSONL remain as fallback
        pass


def send_results_email(
    recipient_email,
    score,
    band,
    strengths,
    weaknesses,
    roadmap,
    lessons,
):
    smtp_host = st.secrets.get("SMTP_HOST")
    smtp_port = int(st.secrets.get("SMTP_PORT", 0))
    smtp_user = st.secrets.get("SMTP_USER")
    smtp_password = st.secrets.get("SMTP_PASSWORD")
    from_email = st.secrets.get("FROM_EMAIL")
    from_name = st.secrets.get("FROM_NAME")

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_email, from_name]):
        raise ValueError(
            "Missing SMTP configuration in Streamlit secrets. "
            "Please set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, FROM_NAME."
        )

    msg = EmailMessage()
    msg["Subject"] = f"Your Inventor Readiness Score: {score}/100 ({band})"
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = recipient_email

    body_lines = [
        f"Inventor Readiness Score: {score}/100",
        f"Score Category: {band}",
        "",
        "Strengths:",
    ]
    body_lines += [f"- {item}" for item in strengths]
    body_lines += ["", "Weaknesses:"]
    body_lines += [f"- {item}" for item in weaknesses]
    body_lines += ["", "Recommended Next Steps:"]
    body_lines += [f"{i}. {step}" for i, step in enumerate(roadmap, start=1)]
    body_lines += ["", "Recommended Inventor Academy Lessons:"]
    body_lines += [f"- {lesson}" for lesson in lessons]
    body_lines.append("")
    body_lines.append("Sent by InventorPath.ai")

    msg.set_content("\n".join(body_lines))

    if smtp_port == 465:
        smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
    else:
        smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        if smtp_port == 587:
            smtp.starttls()

    with smtp:
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)


if st.button("Save your score and continue building your invention"):
    score, section_scores = score_invention()
    band = score_band(score)
    strengths = generate_strengths(section_scores)
    weaknesses = generate_weaknesses(section_scores)
    roadmap = generate_roadmap(section_scores)
    lessons = generate_academy_lessons(section_scores)

    st.divider()
    st.header("InventorPath.ai Score Report")
    st.subheader(f"Your readiness score: {score}/100 — {band}")
    st.write(
        "This result shows where your idea is today and what to focus on next to move toward investor and patent review readiness."
    )

    score_html = f"""
    <div style='background:#f8fafc;border:1px solid #cbd5e1;border-radius:16px;padding:18px;'>
      <div style='font-size:14px;font-weight:700;color:#0f172a;margin-bottom:10px;'>Overall readiness gauge</div>
      <div style='background:#e2e8f0;border-radius:999px;overflow:hidden;height:28px;'>
        <div style='width:{score}%;background:linear-gradient(90deg, #0ea5e9, #16a34a);height:100%;'></div>
      </div>
      <div style='display:flex;justify-content:space-between;font-size:12px;color:#475569;padding-top:8px;'>
        <span>0</span><span>50</span><span>100</span>
      </div>
    </div>
    """

    score_df = pd.DataFrame.from_dict(section_scores, orient="index", columns=["Score"])
    score_df["Max"] = 20
    score_df = score_df.reset_index().rename(columns={"index": "Category"})

    gauge_col, detail_col = st.columns([2, 3])
    with gauge_col:
        st.markdown(score_html, unsafe_allow_html=True)
        st.metric("Readiness tier", band)
        st.info("Save your score and continue building your invention in InventorPath.ai.")

    with detail_col:
        st.subheader("Category Breakdown")
        st.dataframe(score_df, width="stretch", hide_index=True)
        bar_chart_df = pd.DataFrame({"Score": section_scores}, index=section_scores.keys())
        st.bar_chart(bar_chart_df)

    strengths_col, weaknesses_col = st.columns(2)
    with strengths_col:
        st.subheader("Strengths")
        for item in strengths:
            st.success(item)

    with weaknesses_col:
        st.subheader("Weaknesses")
        for item in weaknesses:
            st.warning(item)

    st.subheader("Recommended Next Steps")
    for i, step in enumerate(roadmap, start=1):
        url = academy_link_for(step)
        st.markdown(f"{i}. [{step}]({url})")

    st.subheader("Recommended Inventor Academy Lessons")
    for lesson in lessons:
        lesson_url = get_academy_url_for(lesson)
        st.markdown(f"- [{lesson}]({lesson_url})")

    st.subheader("Email your results")
    recipient_email = st.text_input(
        "Email results to",
        value=email,
        key="email_results",
    )

    if st.button("Email My Results"):
        if not recipient_email or not recipient_email.strip():
            st.error("Please enter a valid email address to receive your results.")
        else:
            try:
                send_results_email(
                    recipient_email=recipient_email.strip(),
                    score=score,
                    band=band,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    roadmap=roadmap,
                    lessons=lessons,
                )
                st.success(f"Results emailed to {recipient_email.strip()}.")
            except Exception as exc:
                st.error(f"Failed to send email: {exc}")

    st.markdown(
        "---\n"
        "### Upgrade to support your next phase\n"
        "- **Free Tier**: Score your idea and explore the basics.\n"
        "- **Guided Builder**: Follow a structured invention development path.\n"
        "- **Professional Review**: Get expert concept and prototype feedback.\n"
        "- **Attorney Partner Review**: Prepare your invention for patent review.\n"
    )

    save_submission(score, section_scores, band, strengths, weaknesses, roadmap)
    st.success(f"Saved assessment to {SUBMISSIONS_CSV} and {ROADMAP_JSONL}.")

st.divider()
st.caption(
    "Disclaimer: This is an educational readiness tool, not legal, patent, financial, or business advice. "
    "Consult a qualified patent attorney or business professional before making major decisions."
)
