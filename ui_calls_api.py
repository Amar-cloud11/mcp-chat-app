
import requests
import streamlit as st

# FastAPI backend address
# API_URL = "http://127.0.0.1:8000"
API_URL = "http://127.0.0.1:8001"
CHAT_URL = f"{API_URL}/chat"
HEALTH_URL = f"{API_URL}/health"

st.set_page_config(
    page_title="MCP Chat App",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 MCP Chat Assistant")
st.caption("Powered by FastAPI + MCP ")

# Check backend status
with st.sidebar:
    st.header("Connection Status")

    try:
        health_response = requests.get(HEALTH_URL, timeout=3)
        if health_response.ok:
            st.success("FastAPI backend connected")
            health_data = health_response.json()
            st.write("Transport:", health_data.get("transport", "Unknown"))
            
        else:
            st.warning(f"Backend returned {health_response.status_code}")
    except requests.RequestException:
        st.error("Backend unavailable")
        st.caption("Start FastAPI on port 8000.")

    st.divider()
    st.write("**Try asking:**")
    st.write("- What is the weather in Chennai?")
    st.write("- What is the Bitcoin price?")

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Initialize conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display earlier messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input box
user_query = st.chat_input("Ask about weather, crypto, or available tools...")

if user_query:
    # Display and save the user's message
    st.session_state.messages.append(
        {"role": "user", "content": user_query}
    )

    with st.chat_message("user"):
        st.markdown(user_query)

    # Send request to FastAPI
    with st.chat_message("assistant"):
        with st.spinner("Calling MCP tool..."):
            try:
                response = requests.post(
                    CHAT_URL,
                    json={"query": user_query},
                    timeout=120,
                )

                if response.ok:
                    data = response.json()
                    answer = data.get("answer", "No answer returned.")
                else:
                    try:
                        detail = response.json().get(
                            "detail", response.text
                        )
                    except ValueError:
                        detail = response.text

                    answer = (
                        f"**Request failed ({response.status_code})**\n\n"
                        f"{detail}"
                    )

            except requests.exceptions.Timeout:
                answer = (
                    "The request timed out. Check whether the MCP tool "
                    "is taking too long to respond."
                )

            except requests.exceptions.ConnectionError:
                answer = (
                    "Cannot connect to FastAPI. Make sure the backend "
                    "is running at http://127.0.0.1:8000."
                )

            except requests.RequestException as error:
                answer = f"Request error: {error}"

        st.markdown(answer)

    # Save the assistant response
    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
