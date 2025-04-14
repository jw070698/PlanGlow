import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Spinner from './Spinner';
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getFirestore, doc, getDoc, setDoc, updateDoc, increment } from "firebase/firestore";
const firebaseConfig = {
    apiKey: "AIzaSyDEu_plavdpqEAY4DRU-x-EKWzhtFR8Q6o",
    authDomain: "plan-glow.firebaseapp.com",
    projectId: "plan-glow",
    storageBucket: "plan-glow.firebasestorage.app",
    messagingSenderId: "586642379491",
    appId: "1:586642379491:web:ac5aeb242cdfac5f462bd6",
    measurementId: "G-448RWVVP9Z"
  };
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const db = getFirestore(app);
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:1350';

const Editable = ({ formData, setResponsePlan , setStudyPlan, participantsId}) => {

    const [originalPlan, setOriginalPlan] = useState(null);
    const [updatedPlan, setUpdatedPlan] = useState(null);
    const [inlineCount, setInlineCount] = useState(0);
    const fetchParticipantData = async () => {
        try {
            const participantRef = doc(db, "messages", participantsId);
            const participantDoc = await getDoc(participantRef);
    
            if (participantDoc.exists()) {
                const data = participantDoc.data();
                setInlineCount(data.inline_count || 0); // Initialize inline count from Firestore
            } else {
                console.log("No data found for this participantsId:", participantsId);
            }
        } catch (error) {
            console.error("Error fetching participant data:", error);
        }
    };
    
    // Call fetchParticipantData when the component mounts
    useEffect(() => {
        fetchParticipantData();
    }, []);
    
    const initialEditableData = {
        background: formData.background,
        topic: formData.topic,
        studyMaterials: formData.studyMaterials,
        duration: {
            months: formData.duration?.months,
            weeks: formData.duration?.weeks,
            days: formData.duration?.days
        },
        availableTime: formData.availableTime
    };
    const [editableData, setEditableData] = useState(initialEditableData);
    const [dropdownVisible, setDropdownVisible] = useState({
        background: false,
        studyMaterials: false
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        setEditableData(initialEditableData);
    }, [formData]);

    const getInitialResponse = async (userMessage) => {
        try {
            const response = await axios.post(`${API_BASE_URL}/response`, {
                user_message: userMessage,
                participantId: participantsId,
            });
            return response.data.response; // Returns initial response
        } catch (error) {
            console.error('Error getting initial response:', error);
            return null;
        }
    };
    const getCritiqueResponse = async () => {
        try {
            const response = await axios.post(`${API_BASE_URL}/response/critique`, {
                participantId: participantsId,
            });
            return response.data.response; // Returns critique response
        } catch (error) {
            console.error('Error getting critique response:', error);
            return null;
        }
    };
    const getImprovedResponse = async () => {
        try {
            const response = await axios.post(`${API_BASE_URL}/response/improved`, {
                participantId: participantsId,
            });
            return response.data.response; // Returns improved response
        } catch (error) {
            console.error('Error getting improved response:', error);
            return null;
        }
    };
    
   // Function to update the API with the new data
    const updateAPI = async (updatedData) => {
        setLoading(true);
        const { topic, background, studyMaterials, duration, availableTime } = updatedData;
        const updated_userMessage = `Create a study plan for a ${background} student on ${topic} using YouTube over ${duration.months} months, ${duration.weeks} weeks, and ${duration.days} days with ${availableTime} hours available per day.`;
        try {
            // Step 1: Initial Response
            const initialResponse = await getInitialResponse(updated_userMessage);
            if (!initialResponse) throw new Error('Failed to fetch initial response');

            console.log('Initial Response:', initialResponse);

            // Step 2: Critique Response
            const critiqueResponse = await getCritiqueResponse();
            if (!critiqueResponse) throw new Error('Failed to fetch critique response');

            console.log('Critique Response:', critiqueResponse);

            // Step 3: Improved Response
            const improvedResponse = await getImprovedResponse();
            if (!improvedResponse) throw new Error('Failed to fetch improved response');
            console.log('Improved Response:', improvedResponse);


            const parsedResponse = typeof improvedResponse === 'string'
                ? JSON.parse(improvedResponse)
                : improvedResponse;

            console.log('Parsed Improved Response:', parsedResponse);

            if (!parsedResponse.studyPlan) {
                console.warn('Parsed response is missing studyPlan. Falling back to initial response.');
                setOriginalPlan(initialResponse);
                setResponsePlan(initialResponse);
                setStudyPlan(initialResponse.studyPlan || {});
                setUpdatedPlan(initialResponse);
                return;
            }

            // Save the improved response
            setOriginalPlan(parsedResponse);
            setResponsePlan(parsedResponse);
            setStudyPlan(parsedResponse.studyPlan);
            setUpdatedPlan(parsedResponse);
            console.log('Study plan successfully updated.');
            
        } catch (error) {
            console.error('Error updating API:', error);
        } finally {
            setLoading(false);
        }
    };    

    const handleEdit = async (key, subkey = null) => {
        if (key === 'background') {
            setDropdownVisible(prev => ({ ...prev, background: !prev.background, studyMaterials: false }));
        } else if (key === 'studyMaterials') {
            setDropdownVisible(prev => ({ ...prev, studyMaterials: !prev.studyMaterials, background: false }));
        } else {
            const newValue = prompt(`Enter new value for ${subkey ? `${key} ${subkey}` : key}`, subkey ? editableData[key][subkey] : editableData[key]);

            if (newValue !== null) {
                const updatedData = subkey 
                    ? {
                        ...editableData,
                        [key]: {
                            ...editableData[key],
                            [subkey]: newValue
                        }
                    } 
                    : {
                        ...editableData,
                        [key]: newValue
                    };

                setEditableData(updatedData);
                updateAPI(updatedData);

                try {
                    const participantRef = doc(db, "messages", participantsId);
                    await updateDoc(participantRef, {
                        inline_count: increment(1)
                    });
                    setInlineCount((prevCount) => prevCount + 1); // Update local count
                } catch (error) {
                    console.error("Error updating inline count:", error);
                }
            }
        }
    };

    const handleSelect = (key, newValue) => {
        const updatedData = {
            ...editableData,
            [key]: newValue
        };

        setEditableData(updatedData);
        setDropdownVisible(prevState => ({
            ...prevState,
            [key]: false
        }));

        updateAPI(updatedData);
    };

    const handleMouseEnter = (e) => {
        e.currentTarget.style.backgroundColor = dropdownItemHoverStyle.backgroundColor;
    };

    const handleMouseLeave = (e) => {
        e.currentTarget.style.backgroundColor = '#FFF';
    };

    const backgroundOptions = ['Novice', 'Advanced Beginner', 'Competence', 'Proficiency', 'Expertise', 'Mastery'];
    const studyMaterialsOptions = ['YouTube', 'Blog'];

    return (
        <div style={{ position: 'relative' }}>
            <h3>
                For a/an
                <button 
                    onClick={() => handleEdit('background')} 
                    style={buttonStyle}
                >
                    {editableData.background}
                </button> 
                student on 
                <button 
                    onClick={() => handleEdit('topic')} 
                    style={buttonStyle}
                >
                    {editableData.topic}
                </button> 
                using 
                YouTube
                over 
                <button 
                    onClick={() => handleEdit('duration', 'months')} 
                    style={buttonStyle}
                >
                    {editableData.duration.months}
                </button> month 
                <button 
                    onClick={() => handleEdit('duration', 'weeks')} 
                    style={buttonStyle}
                >
                    {editableData.duration.weeks}
                </button> week 
                <button 
                    onClick={() => handleEdit('duration', 'days')} 
                    style={buttonStyle}
                >
                    {editableData.duration.days}
                </button> day 
                with 
                <button 
                    onClick={() => handleEdit('availableTime')} 
                    style={buttonStyle}
                >
                    {editableData.availableTime}
                </button> 
                hour available per day
            </h3>
            {loading && <Spinner />}
            {dropdownVisible.background && (
                <div style={{ ...dropdownStyle, top: '2rem', left: '25px' }}>
                    {backgroundOptions.map(option => (
                        <div 
                            key={option} 
                            style={dropdownItemStyle}
                            onClick={() => handleSelect('background', option)}
                            onMouseEnter={handleMouseEnter}
                            onMouseLeave={handleMouseLeave}
                        >
                            {option}
                        </div>
                    ))}    
                </div>
            )}
            
        </div>
    );
};

const buttonStyle = {
    background: 'none',
    border: 'none',
    borderBottom: '1px dashed #007bff',
    color: '#007bff',
    cursor: 'pointer',
    padding: '2px 5px',
    fontSize: '16px',
    display: 'inline-flex',
    alignItems: 'center'
};

const dropdownStyle = {
    position: 'absolute',
    backgroundColor: '#FFF',
    border: '1px solid #ccc',
    borderRadius: '4px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    zIndex: 1000,
    padding: '5px 0',
    minWidth: '150px',
};

const dropdownItemStyle = {
    padding: '8px 12px',
    cursor: 'pointer',
    borderBottom: '1px solid #eee',
};

const dropdownItemHoverStyle = {
    backgroundColor: '#f0f0f0',
};

export default Editable;
