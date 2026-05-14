import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from voyageur import (
    extract_brief,
    generate_itinerary,
    refine_or_answer,
    format_brief,
    format_itinerary,
    build_memory_context,
    save_session_preferences,
    debug_memories,
)
from schemas import TripBrief, Itinerary


USER_ID = "priya"
SEPARATOR = "-" * 60

if "phase" not in st.session_state:
    memory_context = build_memory_context(USER_ID)
    greeting = "Welcome to **Voyageur**! ✈️"
    if memory_context:
        greeting += (
            f"\n\nWelcome back, **{USER_ID.capitalize()}**. "
            "I remember you from our last conversation. "
        )

    st.session_state.phase = "initial"
    st.session_state.memory_context = memory_context
    st.session_state.greeting = greeting
    st.session_state.history = []
    st.session_state.itinerary = None
    st.session_state.messages = []


def render_brief(brief: TripBrief):
    st.markdown("### Trip Brief")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Destination:** {brief.destination}")
        st.markdown(f"**Duration:** {brief.duration_days} day(s)")
        st.markdown(f"**Travelers:** {brief.num_travelers}")
        st.markdown(f"**Budget:** {brief.budget_tier}")
    with col2:
        st.markdown(f"**Pace:** {brief.pace}")
        st.markdown(f"**Interests:** {', '.join(brief.interests)}")
        st.markdown(f"**Dietary:** {', '.join(brief.dietary_needs) if brief.dietary_needs else 'None'}")
        if brief.notes:
            st.markdown(f"**Notes:** {brief.notes}")


def render_block(block, label: str):
    cost = f"₹{block['estimated_cost_inr']:,.0f}" if block["estimated_cost_inr"] else "Free"
    with st.container(border=True):
        cols = st.columns([2, 3, 1, 1])
        cols[0].markdown(f"**{label}**")
        cols[1].markdown(f"{block['activity']}")
        cols[2].markdown(f"{block['duration_minutes']} min")
        cols[3].markdown(cost)
        if block["notes"]:
            st.caption(f"📍 {block['location']} — {block['notes']}")
        else:
            st.caption(f"📍 {block['location']}")


def render_itinerary(it: Itinerary):
    it_data = it.model_dump()
    st.markdown("### Itinerary")
    st.markdown(f"**{it.brief.destination}** · {it.brief.duration_days} days · {it.brief.pace} pace")
    st.markdown("---")

    for day in it_data["days"]:
        with st.expander(f"Day {day['day_number']}", expanded=True):
            render_block(day["morning"], "🌅 Morning")
            render_block(day["afternoon"], "☀️ Afternoon")
            render_block(day["evening"], "🌙 Evening")

    total = f"₹{it.total_estimated_cost:,.0f}" if it.total_estimated_cost else "Not calculated"
    st.markdown(f"### Total Estimated Cost: {total}")


st.set_page_config(page_title="Voyageur", page_icon="✈️", layout="wide")
st.title("✈️ Voyageur")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["type"] == "brief":
            render_brief(msg["data"])
        elif msg["type"] == "itinerary":
            render_itinerary(msg["data"])
        elif msg["type"] == "memories":
            st.code(msg["content"], language="text")
        else:
            st.markdown(msg["content"])

if st.session_state.phase == "initial":
    with st.chat_message("assistant"):
        st.markdown(st.session_state.greeting)
        st.markdown("Describe your ideal trip in plain English.")

    query = st.chat_input("Describe your trip...")
    if query:
        st.session_state.messages.append({"role": "user", "type": "text", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        st.session_state.history.append({"role": "user", "content": f"User description: {query}"})

        with st.spinner("Creating your trip brief..."):
            try:
                brief = extract_brief(query)
            except Exception as e:
                st.error(f"Failed to create trip brief: {e}")
                st.stop()

        st.session_state.history.append({"role": "assistant", "content": f"Extracted brief: {brief.model_dump_json()}"})

        with st.chat_message("assistant"):
            render_brief(brief)
        st.session_state.messages.append({"role": "assistant", "type": "brief", "data": brief})

        with st.spinner("Generating your itinerary..."):
            try:
                itinerary = generate_itinerary(brief)
            except Exception as e:
                st.error(f"Failed to generate itinerary: {e}")
                st.stop()

        st.session_state.history.append({"role": "assistant", "content": f"Initial itinerary: {itinerary.model_dump_json()}"})
        st.session_state.itinerary = itinerary

        with st.chat_message("assistant"):
            render_itinerary(itinerary)
        st.session_state.messages.append({"role": "assistant", "type": "itinerary", "data": itinerary})

        st.session_state.phase = "chatting"
        st.rerun()

elif st.session_state.phase == "chatting":
    with st.chat_message("assistant"):
        st.markdown("You can refine your trip, ask questions, or request alternatives.")
        st.caption("Type `exit` to end · Type `/memories` to see saved preferences")

    query = st.chat_input("Ask something or refine your trip...")
    if query:
        if query.lower() in ("exit", "quit"):
            st.session_state.phase = "ended"
            st.session_state.messages.append({"role": "user", "type": "text", "content": query})
            st.rerun()

        elif query == "/memories":
            result = debug_memories(USER_ID)
            st.session_state.messages.append({"role": "user", "type": "text", "content": query})
            st.session_state.messages.append({"role": "assistant", "type": "memories", "content": result})
            st.rerun()

        else:
            st.session_state.messages.append({"role": "user", "type": "text", "content": query})
            with st.chat_message("user"):
                st.markdown(query)

            st.session_state.history.append({"role": "user", "content": query})

            with st.spinner("Thinking..."):
                try:
                    result_type, result = refine_or_answer(st.session_state.itinerary, query)
                except Exception as e:
                    st.error(str(e))
                    st.stop()

            if result_type == "json" and result is not None:
                st.session_state.itinerary = result
                st.session_state.history.append({"role": "assistant", "content": f"Updated itinerary: {result.model_dump_json()}"})
                with st.chat_message("assistant"):
                    render_itinerary(result)
                st.session_state.messages.append({"role": "assistant", "type": "itinerary", "data": result})
            else:
                st.session_state.history.append({"role": "assistant", "content": str(result)})
                with st.chat_message("assistant"):
                    st.markdown(str(result))
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": str(result)})

            st.rerun()

elif st.session_state.phase == "ended":
    with st.chat_message("assistant"):
        st.markdown("## Final Itinerary")
        if st.session_state.itinerary:
            render_itinerary(st.session_state.itinerary)
        st.markdown("---")

    save_session_preferences(USER_ID, st.session_state.history)
    st.success("Preferences saved. Thank you for using Voyageur!")

    if st.button("Start New Trip"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
