import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { animateScroll } from "react-scroll";
import Modal from 'react-modal';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import './ChatBox.css';
import InputForm from './InputForm';
import CustomMarkdown from './CustomMarkdown';
import Spinner from './Spinner';
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getFirestore, doc, getDoc, setDoc, updateDoc } from "firebase/firestore";


// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyDEu_plavdpqEAY4DRU-x-EKWzhtFR8Q6o",
  authDomain: "plan-glow.firebaseapp.com",
  projectId: "plan-glow",
  storageBucket: "plan-glow.firebasestorage.app",
  messagingSenderId: "586642379491",
  appId: "1:586642379491:web:ac5aeb242cdfac5f462bd6",
  measurementId: "G-448RWVVP9Z"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const db = getFirestore(app);

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:1350';

const ChatBox = () => {
  const [participantsId, setParticipantsId] = useState('');
  const [isIdSubmitted, setIsIdSubmitted] = useState(false);
  const [formData, setFormData] = useState({
    topic: '',
    background: 'novice',
    studyMaterials: [],
    duration: { months: 0, weeks: 0, days: 0 },
    availableTime: 0,
  });
  const [messages, setMessages] = useState([{ type: 'bot', text: 'Hello!', isForm: true }]);
  const [userInput, setUserInput] = useState('');
  const [isFormVisible, setIsFormVisible] = useState(true);
  const [responsePlan, setResponsePlan] = useState('');
  const [infoInput, setInfoInput] = useState('');
  const [modalIsOpen, setModalIsOpen] = useState(false);
  const [resourcesModalIsOpen, setResourcesModalIsOpen] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  // Data - How many time click submit/Send button
  const [submitCount, setSubmitCount] = useState(0);
  const [sendCount, setSendCount] = useState(0);

  const fetchParticipantData = async () => {
    try {
      const participantRef = doc(db, "messages", participantsId);
      const participantDoc = await getDoc(participantRef);

      if (participantDoc.exists()) {
        const data = participantDoc.data();
        setSubmitCount(data.submit_count || 0);
        setSendCount(data.send_count || 0);
      } else {
        console.log("No data found for this participantId:", participantsId);
      }
    } catch (error) {
      console.error("Error fetching participant data:", error);
    }
  };

  // Scroll to bottom
  useEffect(() => {
    animateScroll.scrollToBottom({
      containerId: 'messagesContainer',
      duration: 300,
      smooth: true
    });
  }, [messages]);

  // Enter
  useEffect(() => {
    const handleKeyPress = (event) => {
      if (event.key === 'Enter') {
        if (isFormVisible) {
          handleFormSubmit();
        } else if (userInput.trim() !== '') {
          handleUserInputSubmit();
        }
      }
    };
    window.addEventListener('keydown', handleKeyPress);
    return () => {
      window.removeEventListener('keydown', handleKeyPress);
    };
  }, [messages, formData, userInput, isFormVisible]);

  // Participant ID - Change
  const handleParticipantIdChange = (e) => {
    setParticipantsId(e.target.value);
  };

  // Participant ID - Submit
  const handleParticipantIdSubmit = async (e) => {
    e.preventDefault();
    if (participantsId) {
      setIsIdSubmitted(true);
      await fetchParticipantData();
    } else {
      alert("Please enter a valid Participant ID");
    }
  };

  //
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (type === 'checkbox') {
      setFormData((prev) => ({
        ...prev,
        studyMaterials: checked
          ? [...prev.studyMaterials, value]
          : prev.studyMaterials.filter((material) => material !== value)
      }));
    } else if (['months', 'weeks', 'days'].includes(name)) {
      setFormData((prev) => ({
        ...prev,
        duration: { ...prev.duration, [name]: Number(value) },
      }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  // Input form - Submit
  const handleFormSubmit = async () => {
    setLoading(true);
    const { topic, background, duration, availableTime } = formData;
    const userMessage = `Create a study plan for a ${background} student on ${topic} using YouTube over ${duration.months} months, ${duration.weeks} weeks, and ${duration.days} days with ${availableTime} hours available per day.`;
    setMessages((prevMessages) => [...prevMessages, { type: 'user', text: userMessage }]);

    try {
        // Step 1: Initial response
        const initialResponse = await getInitialResponse(userMessage);
        if (!initialResponse) throw new Error('Failed to get initial response');

        // Step 2: Critique response
        const critiqueResponse = await getCritiqueResponse();
        if (!critiqueResponse) throw new Error('Failed to get critique response');

        // Step 3: Improved response
        const improvedResponse = await getImprovedResponse();
        if (!improvedResponse) throw new Error('Failed to get improved response');

        const participantRef = doc(db, "messages", participantsId);

        // Increment submit_count in Firestore
        await updateDoc(participantRef, {
          submit_count: submitCount + 1,
        });
  
        setSubmitCount((prevCount) => prevCount + 1); 

        setResponsePlan(improvedResponse);
        setMessages((prevMessages) => [
            ...prevMessages,
            { type: 'bot', text: typeof improvedResponse === 'object' ? JSON.stringify(improvedResponse, null, 2) : improvedResponse, isForm: false }
          ]);

        setIsFormVisible(false);
    } catch (error) {
        setMessages((prevMessages) => [
            ...prevMessages,
            { type: 'bot', text: 'Error', isForm: false }
        ]);
    } finally {
        setLoading(false);
    }
};

// Step 1: Initial response
const getInitialResponse = async (userMessage) => {
    try {
        const response = await axios.post(`${API_BASE_URL}/response`, {
            user_message: userMessage,
            participantId: participantsId
        });
        const newResponsePlan = response.data.response;
        return newResponsePlan;
    } catch (error) {
        console.error('Error getting initial response:', error);
        return null;
    }
};

// Step 2: Critique response
const getCritiqueResponse = async () => {
    try {
        const response = await axios.post(`${API_BASE_URL}/response/critique`, {
            participantId: participantsId
        });
        const critiquePlan = response.data.response;
        return critiquePlan;
    } catch (error) {
        console.error('Error getting critique response:', error);
        return null;
    }
};

// Step 3: Improved response
const getImprovedResponse = async () => {
    try {
        const response = await axios.post(`${API_BASE_URL}/response/improved`, {
            participantId: participantsId
        });
        const improvedPlan = response.data.response;
        return improvedPlan;
    } catch (error) {
        console.error('Error getting improved response:', error);
        return null;
    }
};

// 
const handleUserInputChange = (e) => {
  setUserInput(e.target.value);
};

// 
const handleUserInputSubmit = async () => {
  if (userInput.trim() === '') return;
    setMessages((prevMessages) => [...prevMessages, { type: 'user', text: userInput }]);
    setUserInput('');
    setLoading(true);
  try {
    const response = await axios.post(`${API_BASE_URL}/response`, { 
      user_message: userInput,
      participantId: participantsId 
    });

    let responseText = response.data.response;

    if (typeof responseText === 'object') {
      responseText = JSON.stringify(responseText, null, 2); 
    }
    setResponsePlan(responseText);
    setMessages((prevMessages) => [...prevMessages, { type: 'bot', text: responseText, isForm: false }]);

    // Data - counting the clicking of send button
    const participantRef = doc(db, "messages", participantsId);
    await updateDoc(participantRef, {
      send_count: (sendCount || 0) + 1, // increment by 1
    });
    setSendCount((prevCount) => prevCount + 1);

  } catch (error) {
      setMessages((prevMessages) => [...prevMessages, { type: 'bot', text: 'Error fetching response.', isForm: false }]);
  } finally {
      setLoading(false); 
  }
};

const handleInfoClick = async () => {
  setLoading(true);
  const infoMessage = `Can you explain more about the background knowledge levels for the topic: ${formData.topic}?`;
  try {
    if (formData.topic) {
      const response = await axios.post(`${API_BASE_URL}/info`, { 
        info_message: infoMessage});
        setInfoInput(response.data.response);
        setModalIsOpen(true);
      } else {
        alert('Please input topic first');
      }
  } catch (error) {
      alert('Error fetching response from OpenAI');
  } finally {
      setLoading(false); 
    }
  };

const handleResourcesClick = async () => {
  if (!formData.topic) {
    alert('Please input a topic first');
    return;
  }
  setLoading(true);
  try {
    const response = await axios.post(`${API_BASE_URL}/search`, { 
      search_message: formData.topic, 
      participantId: participantsId });

    const items = response.data.response.items || [];
    const formattedResults = items.map(item => ({
      url: `https://www.youtube.com/watch?v=${item.id.videoId}`,
      thumbnail: item.snippet.thumbnails.default.url,
      title: item.snippet.title,
      description: item.snippet.description,
    }));
    setSearchResults(formattedResults.length ? formattedResults : [{ title: 'No resources found', description: '', url: '', thumbnail: '' }]);
    setResourcesModalIsOpen(true);
  } catch (error) {
      alert('Error fetching additional resources');
  } finally {
      setLoading(false);
  }
};

const closeModal = () => setModalIsOpen(false);
const closeResourcesModal = () => setResourcesModalIsOpen(false);


return (
    <div style={styles.container}>
      {!isIdSubmitted ? (
        <form onSubmit={handleParticipantIdSubmit} style={styles.participantIdForm}>
          <input 
            type="text" 
            placeholder="Enter Participant ID" 
            value={participantsId} 
            onChange={handleParticipantIdChange} 
            required
          />
          <button type="submit" style={styles.sendidButton} >Submit</button>
        </form>
      ) : (
        <div style={styles.welcomemsg}>Welcome, Participant {participantsId}</div>
      )}

      <div id="messagesContainer" style={styles.messages}>
        {messages.map((message, index) => (
          <div key={index} style={message.type === 'user' ? styles.userMessage : styles.botMessage}>
            {message.isForm ? (
              <InputForm
                formData={formData}
                handleInputChange={handleInputChange}
                handleFormSubmit={handleFormSubmit}
                handleInfoClick={handleInfoClick}
                handleResourcesClick={handleResourcesClick}
              />
            ) : (
              typeof message.text === 'string' && message.text.trim().startsWith('{') && message.text.trim().endsWith('}')
                ? <CustomMarkdown markdownText={message.text} formData={formData} setResponsePlan={setResponsePlan} participantsId={participantsId}/>
                : <ReactMarkdown
                    children={message.text}
                    remarkPlugins={[remarkGfm, remarkBreaks]}
                  />       
              )}
          </div>
        ))}
        {loading && <Spinner />}
      </div>

      {!isFormVisible && (
        <div style={styles.userInputContainer}>
          <input
            type="text"
            placeholder="Type here..."
            value={userInput}
            onChange={handleUserInputChange}
            style={styles.userInput}
          />
          <button onClick={handleUserInputSubmit} style={styles.sendButton}>Send</button>
        </div>
      )}

      <Modal
        isOpen={modalIsOpen}
        onRequestClose={closeModal}
        contentLabel="Markdown Info"
        style={{
          content: {
            maxWidth: '800px',
            margin: 'auto',
            padding: '2rem',
            borderRadius: '12px'
          }
        }}
      >
        <h2 style={{ textAlign: 'center', marginBottom: '1rem' }}>
          Background Knowledge Levels
        </h2>
        <button 
          onClick={closeModal}
          style={{
            position: 'absolute',
            top: '1rem',
            right: '1rem',
            background: 'transparent',
            border: 'none',
            fontSize: '1rem',
            cursor: 'pointer',
            color: '#888'
          }}
          aria-label="Close"
        >
          ✖
        </button>
        <div 
          className="background-info-html" 
          dangerouslySetInnerHTML={{ __html: infoInput }} 
        />
      </Modal>

      <Modal
        isOpen={resourcesModalIsOpen}
        onRequestClose={closeResourcesModal}
        contentLabel="Additional Resources"
        style={{
          ...styles.modal,
          content: {
            ...styles.modal?.content,
            position: 'relative',
            padding: '2rem',
            maxWidth: '800px',
            margin: 'auto',
            borderRadius: '12px'
          }
        }}
      >
        <button 
          onClick={closeResourcesModal}
          style={{
            position: 'absolute',
            top: '1rem',
            right: '1rem',
            background: 'transparent',
            border: 'none',
            fontSize: '1rem',
            cursor: 'pointer',
            color: '#888'
          }}
          aria-label="Close"
        >
          ✖
        </button>
      </Modal>
    </div>
  );
};

const styles = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', width: '100%', padding: '10px', boxSizing: 'border-box' },
  messages: { flex: 1, overflowY: 'auto', marginBottom: '10px' },
  participantIdForm: {margin: '5px 5px'},
  sendidButton: {borderRadius: '5px', border: 'none', backgroundColor: 'White', color: 'Black', cursor: 'pointer', marginLeft: '5px' },
  welcomemsg: {marginBottom: '5px'},
  userMessage: { padding: '10px', border: 'none', margin: '10px 250px', borderRadius: '15px', backgroundColor: '#d1f5d3', alignSelf: 'flex-end', maxWidth: '80%', wordWrap: 'break-word', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', fontSize: '16px', marginRight: '1px' },
  botMessage: { padding: '10px', borderRadius: '15px', backgroundColor: '#d0e7ff', alignSelf: 'flex-start', maxWidth: '80%', wordWrap: 'break-word', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', fontSize: '16px', marginRight: 'auto' },
  userInputContainer: { display: 'flex', alignItems: 'center', borderTop: '1px solid #ccc', padding: '10px 0' },
  userInput: { flex: 1, padding: '10px', borderRadius: '5px', border: '1px solid #ccc', fontSize: '16px' },
  sendButton: { padding: '10px 20px', borderRadius: '5px', border: 'none', backgroundColor: '#007bff', color: '#fff', cursor: 'pointer', marginLeft: '10px', fontSize: '16px' },
};

export default ChatBox;