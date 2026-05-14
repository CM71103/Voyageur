import sys
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


USER_ID = "priya"
SEPARATOR = "-" * 60


def main():
    memory_context = build_memory_context(USER_ID)

    greeting = "Welcome to Voyageur!"
    if memory_context:
        greeting += (
            f"\n\nWelcome back, {USER_ID.capitalize()}. "
            "I remember you from our last conversation. "
        )

    print("=" * 60)
    print(greeting)
    print(SEPARATOR)
    print("Describe your ideal trip in plain English.")
    print("(e.g., 'I want a 5-day trip to Kyoto with my partner, relaxed pace, mid budget')")
    print("=" * 60)
    print()

    user_description = input("You: ").strip()
    if not user_description:
        print("No input received. Goodbye!")
        sys.exit(0)

    history: list = []

    system_with_memory = "You are Voyageur, an expert travel planning assistant."
    if memory_context:
        system_with_memory += f"\n\n{memory_context}"

    print()
    print("Processing your trip...")
    print()

    try:
        brief = extract_brief(user_description)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to connect to the API. Check your key and model: {e}")
        sys.exit(1)

    history.append({"role": "user", "content": f"User description: {user_description}"})
    history.append({"role": "assistant", "content": f"Extracted brief: {brief.model_dump_json()}"})

    print(format_brief(brief))
    print()

    try:
        itinerary = generate_itinerary(brief)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to generate itinerary: {e}")
        sys.exit(1)

    history.append({"role": "assistant", "content": f"Initial itinerary: {itinerary.model_dump_json()}"})

    print(format_itinerary(itinerary))

    _chat_loop(itinerary, history)


def _chat_loop(itinerary, history):
    print(SEPARATOR)
    print("You can now refine your trip, ask questions, or request alternatives.")
    print("Type 'exit' or 'quit' to end the session.")
    print("Type '/memories' to see stored memories.")
    print(SEPARATOR)
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            break

        if user_input == "/memories":
            print()
            print(debug_memories(USER_ID))
            print()
            continue

        history.append({"role": "user", "content": user_input})
        print()

        try:
            result_type, result = refine_or_answer(itinerary, user_input)
        except Exception as e:
            print(f"Error: {e}")
            print()
            continue

        if result_type == "json" and result is not None:
            itinerary = result
            history.append({"role": "assistant", "content": f"Updated itinerary: {itinerary.model_dump_json()}"})
            print(format_itinerary(itinerary))
        else:
            history.append({"role": "assistant", "content": str(result)})
            print(str(result))
            print()

    print()
    print(SEPARATOR)
    print("FINAL ITINERARY")
    print(SEPARATOR)
    print(format_itinerary(itinerary))
    print(SEPARATOR)

    print("Saving preferences from this session...")
    save_session_preferences(USER_ID, history)
    print("Preferences saved. Thank you for using Voyageur!")


if __name__ == "__main__":
    main()
