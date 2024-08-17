import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Editable = ({ formData, setResponsePlan , setStudyPlan}) => {
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

    useEffect(() => {
        setEditableData(initialEditableData);
    }, [formData]);

    // Function to update the API with the new data
    const updateAPI = async (updatedData) => {
        try {
            const { topic, background, studyMaterials, duration, availableTime } = updatedData;
            const updated_userMessage = `Create a study plan for a ${background} student on ${topic} using ${studyMaterials.join(', ')} over ${duration.months} months, ${duration.weeks} weeks, and ${duration.days} days with ${availableTime} hours available per week.`;
            const response = await axios.post('https://ai-curriculum-pi.vercel.app/response', {user_message: updated_userMessage});
            if (response.data?.response) {
                const markdownText = response.data.response;
                const jsonMatch = markdownText.match(/```json([\s\S]*?)```/);
                
                if (jsonMatch && jsonMatch[1]) {
                    try {
                        const jsonData = JSON.parse(jsonMatch[1].trim());
                        // Update the plan
                        setResponsePlan(jsonData); 
                        setStudyPlan(jsonData);
                        console.log('setstudyPlan in editable.js',jsonData);
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
                For a 
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
                <button 
                    onClick={() => handleEdit('studyMaterials')} 
                    style={buttonStyle}
                >
                    {editableData.studyMaterials}
                </button> 
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
                hour available per week
            </h3>

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

            {dropdownVisible.studyMaterials && (
                <div style={{ ...dropdownStyle, top: '2rem', left: '360px' }}>
                    {studyMaterialsOptions.map(option => (
                        <div 
                            key={option} 
                            style={dropdownItemStyle}
                            onClick={() => handleSelect('studyMaterials', option)}
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
    backgroundColor: '#C0C4C2',
    color: '#FFF',
    border: 'none',
    padding: '5px 10px',
    borderRadius: '4px',
    cursor: 'pointer',
    margin: '0 5px',
    fontSize: '1rem',
    transition: 'background-color 0.3s ease',
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
