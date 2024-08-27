import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Spinner from './Spinner';
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:1350';

const Editable = ({ formData, setResponsePlan , setStudyPlan}) => {

    const [originalPlan, setOriginalPlan] = useState(null);
    const [updatedPlan, setUpdatedPlan] = useState(null);
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

    // Function to update the API with the new data
    const updateAPI = async (updatedData) => {
        setLoading(true);
        try {
            const { topic, background, studyMaterials, duration, availableTime } = updatedData;
            const updated_userMessage = `Create a study plan for a ${background} student on ${topic} using ${studyMaterials.join(', ')} over ${duration.months} months, ${duration.weeks} weeks, and ${duration.days} days with ${availableTime} hours available per day.`;
            console.log(updated_userMessage);
            const response = await axios.post(`${API_BASE_URL}/response`, {user_message: updated_userMessage});
            
            if (response.data?.response) {
                const markdownText = response.data.response;
                const jsonMatch = markdownText.match(/```json([\s\S]*?)```/);
                
                if (jsonMatch && jsonMatch[1]) {
                    try {
                        const jsonData = JSON.parse(jsonMatch[1].trim());
    
                        // Store the original plan only if it's not set yet
                        if (!originalPlan) {
                            setOriginalPlan(jsonData);
                        }
    
                        // Update the plan with the new response
                        setResponsePlan(jsonData);
                        setStudyPlan(jsonData);
                        setUpdatedPlan(jsonData); // Store the updated plan
    
                    } catch (jsonError) {
                        console.error('Error parsing JSON:', jsonError);
                    }
                } else {
                    console.error('No JSON content found in the response.');
                }
            } else {
                console.error('No response data from API');
            }
        } catch (error) {
            console.error('Error updating API:', error);
        } finally {
            setLoading(false);
        }
    };    

    const handleEdit = (key, subkey = null) => {
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

    const backgroundOptions = ['Absolute Beginner', 'Beginner', 'Intermediate', 'Advanced'];
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
