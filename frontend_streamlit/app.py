import streamlit as st
import requests

st.set_page_config(page_title="Tunisia Tourism AI", page_icon="🇹🇳")

# Custom CSS for Tunisia theme
st.markdown("""
<style>
    .stChatFloatingInputContainer {
        bottom: 20px;
    }
    .user-avatar {
        background-color: #E70013;
    }
</style>
""", unsafe_allow_html=True)

st.title("🇹🇳 Tunisia Explorer AI")
st.caption("Ask specific questions to get honest reviews based on real-time web search.")

tab1, tab2 = st.tabs(["💬 Chat", "🎥 Video Analyst"])

with tab1:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message and message["sources"]:
                st.markdown("**Sources:**")
                for source in message["sources"]:
                    st.markdown(f"- [{source}]({source})")

    # Input field
    if prompt := st.chat_input("Ask about hotels, food, or places..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Searching the web..."):
                try:
                    # Call local Backend API
                    response = requests.post("http://localhost:8000/ask", json={"question": prompt})
                    if response.status_code == 200:
                        data = response.json()
                        answer = data["answer"]
                        sources = data["sources"]
                        
                        st.markdown(answer)
                        if sources:
                            st.markdown("**Sources:**")
                            for source in sources:
                                st.markdown(f"- [{source}]({source})")
                        
                        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Connection failed: {e}. Make sure backend is running on port 8000.")

with tab2:
    st.header("Video Content Analysis")
    
    mode = st.radio("Mode", ["🎥 Analyze Single URL", "🔍 Search & Learn (RAG)"], horizontal=True)
    
    if mode == "🎥 Analyze Single URL":
        st.write("Paste a video link (YouTube, etc.) to get a detailed description and analysis.")
        video_url = st.text_input("Video URL", placeholder="https://www.youtube.com/watch?v=...")
        
        if st.button("Analyze Video"):
            if video_url:
                with st.spinner("Downloading and watching video... (This may take a moment)"):
                    try:
                        response = requests.post("http://localhost:8000/analyze-video", json={"video_url": video_url})
                        if response.status_code == 200:
                            data = response.json()
                            analysis = data["analysis"]
                            st.success("Analysis Complete!")
                            st.markdown("### 📝 Analysis Result")
                            st.markdown(analysis)
                        else:
                            st.error(f"Error: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"Connection failed: {e}")
            else:
                st.warning("Please enter a video URL.")

    else:
        st.write("Search for videos on a topic, analyze them, and add them to the AI's knowledge base.")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_topic = st.text_input("Topic to Learn About", placeholder="e.g. Tunisia Street Food")
        with col2:
            video_count = st.number_input("Max Videos", min_value=1, max_value=5, value=2)
            
        if st.button("🚀 Search & Learn"):
            if search_topic:
                with st.spinner(f"Searching and analyzing {video_count} videos about '{search_topic}'... This will take time."):
                    try:
                        response = requests.post("http://localhost:8000/index-videos", json={"query": search_topic, "count": video_count})
                        if response.status_code == 200:
                            data = response.json()
                            message = data["message"]
                            videos = data["videos"]
                            
                            st.success(message)
                            
                            st.markdown("### 📼 Processed Videos")
                            for v in videos:
                                status_icon = "✅" if v["status"] == "Indexed" else "❌"
                                st.markdown(f"{status_icon} **[{v['title']}]({v['url']})** - {v['status']}")
                                
                            st.info("The AI has learned from these videos! Go to the 'Chat' tab to ask questions about this topic.")
                        else:
                            st.error(f"Error: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"Connection failed: {e}")
            else:
                st.warning("Please enter a topic.")
