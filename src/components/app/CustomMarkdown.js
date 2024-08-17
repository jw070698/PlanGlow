import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { checkAvailability } from './ReferenceCheck';
import Editable from './Editable';

const CustomMarkdown = ({ markdownText, formData, setResponsePlan }) => {
    // formData: topic, background, studyMaterials, duration, availableTime 
    const [parsedJson, setParsedJson] =  useState(null);
    const [searchResults, setSearchResults] = useState([]);
    const [resourcesModalIsOpen, setResourcesModalIsOpen] = useState(false);
    const [completedItems, setCompletedItems] = useState({});
    const [studyPlan, setStudyPlan] = useState({} || parsedJson.studyPlan); 
    useEffect(() => {
        const jsonMatch = markdownText.match(/```json([\s\S]*?)```/);
        if (jsonMatch) {
            try {
                const jsonData = JSON.parse(jsonMatch[1].trim());
                setParsedJson(jsonData);
                console.log('jsonData in CustomMarkdown.js', jsonData);
            } catch (error) {
                console.error("JSON parsing error:", error);
            }
        }
    }, [markdownText]);

    useEffect(() => {
        if (parsedJson) {
            setStudyPlan(parsedJson.studyPlan);  // Update study plan when parsedJson changes
            if (setResponsePlan) {
                setResponsePlan(parsedJson.studyPlan); // Notify parent component of the updated study plan
                console.log('studyplan',parsedJson.studyPlan);
            }
        }
    }, [parsedJson, setResponsePlan]);

    const handleResourcesClick = async (topic, type) => {
        if (type === 'YouTube') {
            if (!topic) {
                alert('Please provide a topic');
                return;
            }

            try {
                const search_message = `${topic} in ${formData?.topic || ''}`;
                const response = await axios.post('https://ai-curriculum-pi.vercel.app/search', { search_message: search_message });
                const items = response.data.response.items || [];
                const formattedResults = items.map(item => {
                    const thumbnailUrl = item.snippet.thumbnails?.default?.url || 'https://via.placeholder.com/120'; // Fallback URL
                    return {
                        url: `https://www.youtube.com/watch?v=${item.id.videoId}`,
                        thumbnail: thumbnailUrl,
                        title: item.snippet.title,
                        description: item.snippet.description,
                    };
                });
                setSearchResults(formattedResults.length > 0 ? formattedResults : [{ title: 'No resources found', description: '', url: '', thumbnail: '' }]);
                setResourcesModalIsOpen(true);
            } catch (error) {
                alert('Error fetching additional resources');
            }
        } else {
            alert('Resource type is not supported for API requests');
        }
    };

    const handleCheckboxChange = (week, index) => {
        setCompletedItems(prevState => ({
            ...prevState,
            [week]: {
                ...prevState[week],
                [index]: !prevState[week]?.[index]
            }
        }));
    };

    const handleUpdateStudyPlan = (updatedPlan) => {
        setParsedJson(prevState => ({
            ...prevState,
            studyPlan_Overview: updatedPlan.studyPlan_Overview 
        }));
      };

    const renderResources = (resources, topic) => {
        if (typeof resources === 'object' && resources !== null) {
            return Object.keys(resources).map((type, index) => {
                const resource = resources[type];
                return (
                    <div key={index} style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: '#F3F7F3', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <h4 style={{ fontSize: '1rem', margin: '0 0.5rem', color: '#333' }}>{type}</h4>
                            <button 
                                onClick={() => handleResourcesClick(topic, type)}
                                style={{ 
                                    fontSize: '1rem', 
                                    marginLeft: '1rem',
                                    padding: '0.5rem 1rem', 
                                    backgroundColor: '#DAE7DA', 
                                    color: '#4F5452', 
                                    border: 'none', 
                                    borderRadius: '4px', 
                                    cursor: 'pointer',
                                    alignItems: 'center',
                                    lineHeight: '1',
                                }}
                            >
                                🎦 Additional Resources
                            </button>
                            <button 
                            onClick={async () => {
                                const result = await checkAvailability(resource.link);
                                if (result.exists) {
                                    alert(`Video found: ${result.title}`);
                                } else {
                                    alert(result.message);
                                }
                            }} 
                            style={{ 
                                fontSize: '1rem', 
                                marginLeft: '1rem',
                                padding: '0.5rem 1rem', 
                                backgroundColor: '#AFD0BF', 
                                color: '#4F5452', 
                                border: 'none', 
                                borderRadius: '4px', 
                                alignItems: 'center',
                                cursor: 'pointer',
                                lineHeight: '1',
                            }}
                        >
                            Reference Check
                        </button>
                        </div>
                        <p style={{ fontSize: '1rem', margin: '0.5rem 0', marginLeft: '1rem' }}>
                            <strong>Title:</strong> {resource.title}
                        </p>
                        <p style={{ fontSize: '1rem', margin: '0.5rem 0', marginLeft: '1rem' }}>
                            <strong>Link: </strong> 
                            <a 
                                href={resource.link} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                style={{ color: '#3855A7', textDecoration: 'none' }}
                            >
                                {resource.link}
                            </a>
                            {resource && (
                            <img 
                                src={resource.thumbnail} 
                                alt={resource.thumbnail} 
                                style={{ width: '120px', height: 'auto' }} 
                            />
                            )}
                        </p>
                    </div>
                );
            });
        } else {
            return <p>No resources available</p>;
        }
    };

    const renderStudyPlan = (plan) => {
        return Object.keys(plan).map(week => (
            <div key={week} style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '1rem', marginBottom: '1rem', backgroundColor: '#f9f9f9' }}>
                <h3 style={{ borderBottom: '2px solid #ddd', paddingBottom: '0.5rem' }}>{week}</h3>
                {plan[week].map((entry, index) => (
                    <div key={index} style={{ marginBottom: '1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <input 
                                type="checkbox" 
                                style={{ marginRight: '0.5rem' }} 
                                checked={completedItems[week]?.[index] || false}
                                onChange={() => handleCheckboxChange(week, index)}
                            />
                            <p style={{ 
                                fontSize: '1.1rem', 
                                fontWeight: 'bold', 
                                margin: 0, 
                                textDecoration: completedItems[week]?.[index] ? 'line-through' : 'none',
                                color: completedItems[week]?.[index] ? '#aaa' : '#000' 
                            }}>
                                [{entry.day}]
                            </p>
                        </div>
                        <div style={{ marginLeft: '1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <p style={{ 
                                fontSize: '1rem', 
                                fontWeight: 'bold', 
                                margin: '0 0.5rem 0 0' // Adjusted margin to space the text and button
                            }}>
                                Topic:
                            </p>
                            <button 
                                onClick={() => handleResourcesClick(entry.topic, 'YouTube')}
                                style={{ 
                                    fontSize: '1rem', 
                                    padding: '0.3rem 0.6rem', 
                                    backgroundColor: '#EAEBEB', 
                                    color: 'black', 
                                    border: 'none', 
                                    borderRadius: '4px', 
                                    cursor: 'pointer', 
                                    textDecoration: 'none'
                                }}
                            >
                                {entry.topic}
                            </button>
                        </div>
                            <div>
                                {renderResources(entry.resources, entry.topic)}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        ));
    };

    if (parsedJson === null) {
        return <ReactMarkdown>{markdownText}</ReactMarkdown>;
    }

    return (
        <div>
            <h2>Study Plan Overview </h2>
            <Editable formData={formData} setResponsePlan={setParsedJson}  setStudyPlan={handleUpdateStudyPlan}/>
            {parsedJson.studyPlan_Overview && Object.keys(parsedJson.studyPlan_Overview).map(week => (
                <div key={week} style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center' }}>
                    <h3 style={{ margin: '0 1rem 0 0' }}>{week}:</h3>
                    <p style={{ margin: 0 }}>{parsedJson.studyPlan_Overview[week]}</p>
                </div>
            ))}
            <br />
            <h2>Detailed Study Plan</h2>
            {renderStudyPlan(parsedJson.studyPlan)}

            {resourcesModalIsOpen && (
                <div style={{ position: 'fixed', top: '0', left: '0', width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <div style={{ backgroundColor: 'white', padding: '1rem', borderRadius: '8px', maxWidth: '600px', width: '100%', height: '750px', display: 'flex', flexDirection: 'column' }}>
                        <h3>Additional Resources</h3>
                        <div style={{ flex: '1', overflowY: 'auto', marginTop: '1rem' }}>
                            {searchResults.map((result, index) => (
                                <div key={index} style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center' }}>
                                    <img src={result.thumbnail} alt={result.title} style={{ width: '120px', height: '90px', marginRight: '1rem' }} />
                                    <div>
                                        <a href={result.url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{result.title}</a>
                                        <p>{result.description}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                        <button 
                            onClick={() => setResourcesModalIsOpen(false)} 
                            style={{ 
                                fontSize: '1rem', 
                                padding: '0.3rem 0.6rem', 
                                backgroundColor: '#C0C4C2', 
                                color: 'black', 
                                border: 'none', 
                                borderRadius: '4px', 
                                cursor: 'pointer', 
                                textDecoration: 'none'
                            }}
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CustomMarkdown;