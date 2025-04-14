import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './ChatBox.css';
import './Styles.css'; 
import { checkAvailability } from './ReferenceCheck';
import FAQIconStudyPlan from './FAQIconStudyPlan';
import Editable from './Editable';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faThumbsUp, faEye, faCircleCheck, faCaretDown, faCaretRight } from '@fortawesome/free-solid-svg-icons';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
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
  
// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const db = getFirestore(app);

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:1350';

const CustomMarkdown = ({ markdownText, formData, setResponsePlan, participantsId }) => {
    
const [parsedJson, setParsedJson] =  useState(null);
    const [searchResults, setSearchResults] = useState([]);
    const [resourcesModalIsOpen, setResourcesModalIsOpen] = useState(false);
    const [completedItems, setCompletedItems] = useState({});
    const [studyPlan, setStudyPlan] = useState({} || parsedJson.studyPlan); 
    const [videoStatuses, setVideoStatuses] = useState({});
    const [buttonStyles, setButtonStyles] = useState({});
    const [selectedWeekIndex, setSelectedWeekIndex] = useState(null);
    const [selectedDayIndex, setSelectedDayIndex] = useState(null);
    const [tooltipVisible, setTooltipVisible] = useState(false);
    const [explanationContent, setExplanationContent] = useState({}); 
    const [weekVisibility, setWeekVisibility] = useState({});  
    const [dayVisibility, setDayVisibility] = useState({});   
    const [additionalResourcesCount, setAdditionalResourcesCount] = useState(0);
    const [selectCount, setSelectCount] = useState(0);
    const [toggleWeekCount, setToggleWeekCount] = useState(0);
    const [toggleDayCount, setToggleDayCount] = useState(0);


    const fetchParticipantData = async () => {
        try {
          const participantRef = doc(db, "messages", participantsId);
          const participantDoc = await getDoc(participantRef);
    
          if (participantDoc.exists()) {
            const data = participantDoc.data();
            setAdditionalResourcesCount(data.additional_resources_count || 0);
            setSelectCount(data.select_button_count || 0);
          } else {
            console.log("No data found for this participantId:", participantsId);
          }
        } catch (error) {
          console.error("Error fetching participant data:", error);
        }
      };


      const handleToggleWeek = async (week) => {
        const isOpening = !weekVisibility[week];
    
        // Toggle visibility for the week
        setWeekVisibility((prevState) => ({
            ...prevState,
            [week]: isOpening, 
        }));
    
        if (isOpening) {
            // Increment the toggleWeekCount only if the week is being opened
            setToggleWeekCount((prevCount) => prevCount + 1);
    
            try {
                const participantRef = doc(db, "messages", participantsId);
                await updateDoc(participantRef, {
                    toggleWeekCount: increment(1),
                });
            } catch (error) {
                console.error("Error updating toggleWeekCount:", error);
            }
        }
    };
    
    const handleToggleDay = async (week, day, topic) => {
        const isOpening = !dayVisibility[week]?.[day];
    
        setDayVisibility((prevState) => ({
            ...prevState,
            [week]: {
                ...prevState[week],
                [day]: isOpening, 
            },
        }));
    
        if (isOpening) {
            // Increment the toggleDayCount only if the day is being opened
            setToggleDayCount((prevCount) => prevCount + 1);
    
            try {
                const participantRef = doc(db, "messages", participantsId);
                await updateDoc(participantRef, {
                    toggleDayCount: increment(1),
                });
            } catch (error) {
                console.error("Error updating toggleDayCount:", error);
            }
    
            fetchExplanation(topic, week, day);
        }
    };
    

    const formatNumber = (num) => {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'k';
        }
        return num.toString();
    };

    const handleMouseOver = (link) => {
        setTooltipVisible((prevState) => ({
            ...prevState,
            [link]: true
        }));
    };

    const handleSelectVideo = async (weekIndex, dayIndex, selectedVideo) => {
        const weeks = Object.keys(studyPlan); // Get all week keys
        const week = weeks[weekIndex];
        
        if (!week || !studyPlan[week]) {
            console.error('Week is not defined in studyPlan:', week);
            return;
        }
    
        if (dayIndex < 0 || dayIndex >= studyPlan[week].length) {
            console.error('Day index is out of bounds:', dayIndex);
            return;
        }
    
        // Clone the existing study plan to avoid mutating the original one directly
        const updatedPlan = { ...studyPlan };
    
        if (!updatedPlan[week][dayIndex].resources) {
            updatedPlan[week][dayIndex].resources = {};
        }
    
        // Replace the YouTube resource with the selected video details
        updatedPlan[week][dayIndex].resources.YouTube = {
            link: selectedVideo.url,
            title: selectedVideo.title,
            thumbnail: selectedVideo.thumbnail,
            views: selectedVideo.views,
            likes: selectedVideo.likes,
        };
    
        setStudyPlan(updatedPlan); 
    
        setParsedJson((prevState) => {
            const newStudyPlan = { ...prevState.studyPlan };
            newStudyPlan[week] = [...prevState.studyPlan[week]]; 
    
            newStudyPlan[week][dayIndex].resources.YouTube = {
                link: selectedVideo.url,
                title: selectedVideo.title,
                thumbnail: selectedVideo.thumbnail,
                views: selectedVideo.views,
                likes: selectedVideo.likes,
            };
    
            return { ...prevState, studyPlan: newStudyPlan };
        });
    
        setResourcesModalIsOpen(false);
    
        // Increment select_count in Firestore
        try {
            const participantRef = doc(db, "messages", participantsId);
            await updateDoc(participantRef, {
                select_count: increment(1)
            });
            setSelectCount(prevCount => prevCount + 1);  // Update local state
        } catch (error) {
            console.error("Error updating select count:", error);
        }
    };
    

    const handleMouseOut = (link) => {
        setTooltipVisible((prevState) => ({
            ...prevState,
            [link]: false
        }));
    };

    useEffect(() => {
        if (!markdownText) {
            console.error("markdownText is undefined");
            return;
        }
        const jsonMatch = markdownText.match(/```json([\s\S]*?)```/) || markdownText.match(/{[\s\S]*}/);
        if (jsonMatch && jsonMatch[1]) {
            try {
                // Trim any whitespace and parse JSON
                const jsonData = JSON.parse(jsonMatch[1].trim());
                setParsedJson(jsonData);
            } catch (error) {
                console.error("JSON parsing error:", error);
                setParsedJson(null);
            }
        } else if (jsonMatch && jsonMatch[0]) {
            // Handle raw JSON without backticks, in case it matches only jsonMatch[0]
            try {
                const jsonData = JSON.parse(jsonMatch[0].trim());
                setParsedJson(jsonData);
            } catch (error) {
                console.error("JSON parsing error:", error);
                // If parsing fails, set the raw markdown text to display as a fallback
                setParsedJson(null);
            }
        } else {
            console.error("No JSON code block or raw JSON found in markdownText.");
            setParsedJson(null); // No valid JSON found, set to null to fallback to markdown
        }
    }, [markdownText]);
    

    useEffect(() => {
        if (parsedJson) {
            setStudyPlan(parsedJson.studyPlan);  // Update study plan when parsedJson changes
            if (setResponsePlan) {
                setResponsePlan(parsedJson.studyPlan); // Notify parent component of the updated study plan
            }
        }
    }, [parsedJson, setResponsePlan]);

    useEffect(() => {
        if (parsedJson && parsedJson.studyPlan) {
            const updateButtonStyles = async () => {
                const resources = Object.values(parsedJson.studyPlan).flatMap(week => 
                    week.flatMap(day => 
                        // If the resource is an array, flat map it
                        // Else, just return the single resource
                        Object.values(day.resources || {}).flatMap(resource => {
                            return (Array.isArray(resource) ? resource : [resource]).map(item => ({
                                ...item,
                                topic: day.topic || "No Topic" // Assuming each day has a 'topic' field; adjust if named differently
                            }));
                        }
                            // Array.isArray(resource) ? resource : [resource]
                        )
                    )
                );

                const linkStatuses = await Promise.all(resources.map(async resource => {
                    const research_query = `${resource.topic} in ${formData?.topic || ''} for ${formData?.background||''} within ${formData.availableTime || '0'} hours`
                    const result = await checkAvailability(resource.link, participantsId, research_query);
                    return {
                        link: resource.link,
                        backgroundColor: result.exists ? '#AFD0BF' : '#EB5353',
                        color: result.exists ? '#4F5452' : '#FFF'
                    };
                }));
                const updatedButtonStyles = linkStatuses.reduce((acc, { link, backgroundColor, color }) => {
                    acc[link] = { backgroundColor, color };
                    return acc;
                }, {});
                setButtonStyles(updatedButtonStyles);
            };

            updateButtonStyles();
        }
    }, [parsedJson]);

    const extractVideoId = (url) => {
        const urlObj = new URL(url);
        const searchParams = urlObj.searchParams;
        const videoId = searchParams.get('v');
        
        if (!videoId && urlObj.hostname.includes('youtu.be')) {
            return urlObj.pathname.slice(1); 
        }
        
        return videoId;
    };

    useEffect(() => {
        if (parsedJson && parsedJson.studyPlan) {
            const fetchAndStoreVideoStatuses = async () => {
                const resources = Object.values(parsedJson.studyPlan).flatMap(item => 
                    item.flatMap(day => 
                        Object.values(day.resources || {}).flatMap(resourceArray => 
                            Array.isArray(resourceArray) ? resourceArray : [resourceArray]
                        )
                    )
                );

                const videoData = resources.map(resource => {
                    if (!resource || !resource.link) {
                        console.warn('Invalid resource or missing link:', resource);
                        return null;
                    }
    
                    const videoId = extractVideoId(resource.link);
                    const thumbnail = resource.thumbnail || null;
    
                    if (!videoId) {
                        console.warn('Failed to extract video ID from URL:', resource.link);
                        return null;
                    }
    
                    return {
                        link: resource.link,
                        videoId,
                        thumbnail,
                    };
                }).filter(video => video !== null);

                const statuses = await Promise.all(videoData.map(async (data) => {
                    let thumbnail = data.thumbnail;
    
                    if (!thumbnail && data.videoId) {
                        // Call your backend API to get the thumbnail if it's not already present
                        const response = await axios.post(`${API_BASE_URL}/get_thumbnail`, { video_id: data.videoId });
                        thumbnail = response.data.thumbnail || 'https://via.placeholder.com/120';
                    }
    
                    const status = await fetchVideoStatus(data.videoId);
    
                    return {
                        views: status.views,
                        likes: status.likes,
                        thumbnail: thumbnail,
                    };
                }));
                const statusMap = videoData.reduce((acc, data, index) => {
                    acc[data.link] = {
                        views: statuses[index].views,
                        likes: statuses[index].likes,
                        thumbnail: statuses[index].thumbnail || data.thumbnail
                    };
                    return acc;
                }, {});
                setVideoStatuses(statusMap);
            };

            fetchAndStoreVideoStatuses();
        }
    }, [parsedJson]);

    const fetchVideoStatus = async (videoId, query) => {
        if (!videoId) {
            return { views: 'N/A', likes: 'N/A', fallback: true};
        }
        try {
            // Fetch video statistics
            const statsResponse = await axios.post(`${API_BASE_URL}/video_stats`, { video_id: videoId });
            const statsData = statsResponse.data;
        
            return {
                views: statsData.views,
                likes: statsData.likes
            };
        } catch (error) {
            console.error('Error fetching video status:', error); 
            return { views: 'N/A', likes: 'N/A'};
        }
    };

    const handleResourcesClick = async (topic, type, weekIndex, dayIndex) => {
        if (!participantsId) {
            console.error('participantsId is missing.');
            return;
        }
        if (type === 'YouTube') {
            if (!topic) {
                alert('Please provide a topic');
                return;
            }
            setSelectedWeekIndex(weekIndex);
            setSelectedDayIndex(dayIndex);

            try {
                const search_message = `${topic} in ${formData?.topic || ''} for ${formData?.background||''} within ${formData?.availableTime || '0'} hours`; /////////////./////
                console.log("SEARCU", search_message)
                const response = await axios.post(`${API_BASE_URL}/search`, { 
                    search_message: search_message});
                const items = response.data.response.items || [];
                const videoIds = items.map(item => item.id.videoId);
                const statusPromises = videoIds.map(videoId => fetchVideoStatus(videoId));
                const statuses = await Promise.all(statusPromises);
                const formattedResults = items.map((item, index) => {
                    const videoId = item.id.videoId;
                    const status = statuses[index];
                    const thumbnailUrl = item.snippet.thumbnails?.default?.url || 'https://via.placeholder.com/120'; // Fallback URL
                    return {
                        url: `https://www.youtube.com/watch?v=${item.id.videoId}`,
                        thumbnail: thumbnailUrl,
                        title: item.snippet.title,
                        description: item.snippet.description,
                        views: status.views,
                        likes: status.likes
                    };
                });
                console.log("formattedresults",formattedResults);
                setSearchResults(formattedResults.length > 0 ? formattedResults : [{ title: 'No resources found', description: '', url: '', thumbnail: '', views: 'N/A', likes: 'N/A'}]);
                setResourcesModalIsOpen(true);

                const participantRef = doc(db, "messages", participantsId);
                await updateDoc(participantRef, {
                    additional_resources_count: increment(1)
                });

            } catch (error) {
                alert('Error fetching additional resources');
            }
        } else {
            alert('Resource type is not supported for API requests');
        }
    };

    const fetchExplanation = async (topic, week, day) => {
        try {
            // Check if the explanation already exists
            if (explanationContent[week]?.[day]) {
                console.log(`Explanation for ${topic} on ${week} ${day} is already fetched.`);
                return; // If it exists, skip the API call
            }
    
            const [reasonResponse, objectivesResponse] = await Promise.all([
                axios.post(`${API_BASE_URL}/topic-explanations`, { user_message: topic, participantId: participantsId }),
                axios.post(`${API_BASE_URL}/generate-objectives`, { user_message: topic, participantId: participantsId })
            ]);
    
            // Combine the content
            let combinedContent = '';
            if (reasonResponse.data && reasonResponse.data.explanation) {
                combinedContent += `### Reason for studying '${topic}':\n${reasonResponse.data.explanation}\n\n`;
            } else {
                combinedContent += `### Reason for studying '${topic}':\nNo reasons available for this topic.\n\n`;
            }
            if (objectivesResponse.data && objectivesResponse.data.objectives) {
                combinedContent += `### Learning Objectives for '${topic}':\n${objectivesResponse.data.objectives}\n\n`;
            } else {
                combinedContent += `### Learning Objectives for '${topic}':\nNo objectives available for this topic.\n\n`;
            }
    
            // Save the fetched content in the state
            setExplanationContent(prevState => ({
                ...prevState,
                [week]: {
                    ...prevState[week],
                    [day]: combinedContent
                }
            }));
        
        } catch (error) {
            if (error.code === 'ERR_CONNECTION_REFUSED') {
                console.error('Connection Refused: Unable to reach the server.');
            } else if (error.response) {
                // Server responded with a status other than 2xx
                console.error(`API Error: ${error.response.status} - ${error.response.data.detail || error.response.statusText}`);
            } else {
                // Something else happened
                console.error('An unexpected error occurred:', error.message);
            }
            setExplanationContent(prevState => ({
                ...prevState,
                [week]: {
                    ...prevState[week],
                    [day]: 'Error fetching information for this topic. Please try again later.'
                }
            }));
        }
    };
    

    const handleUpdateStudyPlan = (updatedPlan) => {
        setParsedJson(prevState => ({
            ...prevState,
            studyPlan_Overview: updatedPlan.studyPlan_Overview 
        }));
    };

    const renderResources = (resources, topic, weekIndex, dayIndex) => {
        if (typeof resources === 'object' && resources !== null) {
            return Object.keys(resources).map((type) => {
                const resourceArray = resources[type];
                const normalizedResourceArray = Array.isArray(resourceArray) ? resourceArray : [resourceArray];

                return normalizedResourceArray.map((resource, index) => {
                    const resourceStatus = videoStatuses[resource.link] || { views: 'N/A', likes: 'N/A', thumbnail: 'https://via.placeholder.com/120' };
                    return (
                        <div key={`${type}-${index}`} style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: '#F3F7F3', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                                <h4 style={{ fontSize: '1rem', margin: '0 0.5rem', color: '#333' }}>{type}</h4>
                                {resourceStatus.fallback && <span style={{ marginLeft: '0.5rem', color: '#EB5353' }}>Fallback resource</span>}
                                <button 
                                    onClick={() => handleResourcesClick(topic, type, weekIndex, dayIndex)}
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
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', marginTop: '0.5rem' }}>
                                {resourceStatus.thumbnail && (
                                    <img 
                                        src={resourceStatus.thumbnail} 
                                        alt={resource.title} 
                                        style={{ width: '120px', height: 'auto', borderRadius: '4px', marginRight: '1rem' }} 
                                    />
                                )}
                                <p style={{ fontSize: '1rem', margin: '0.5rem 0', marginLeft: '1rem' }}>
                                    <FontAwesomeIcon icon={faThumbsUp} style={{ marginRight: '0.5rem' }} />
                                    {formatNumber(resourceStatus.likes)}
                                    <span style={{ margin: '0 0.5rem' }}>|</span>
                                    <FontAwesomeIcon icon={faEye} style={{ marginRight: '0.5rem' }} />
                                    {formatNumber(resourceStatus.views)}
                                    <div style={{ position: 'relative', display: 'inline-block' }}>
                                        <button 
                                            onMouseOver={() => handleMouseOver(resource.link)}
                                            onMouseOut={() => handleMouseOut(resource.link)}
                                            style={{ 
                                                fontSize: '1rem', 
                                                padding: '0.5rem 1rem', 
                                                backgroundColor: 'transparent', 
                                                color: buttonStyles[resource.link]?.backgroundColor || '#4F5452',
                                                border: 'none', 
                                                borderRadius: '4px', 
                                                alignItems: 'center',
                                                cursor: 'pointer',
                                                lineHeight: '1',
                                            }}
                                        >
                                            <FontAwesomeIcon icon={faCircleCheck} />
                                            {tooltipVisible[resource.link] && (
                                                <strong>
                                                    {buttonStyles[resource.link]?.backgroundColor === '#AFD0BF' ? ' Valid Resource' : ' Invalid Resource'}
                                                </strong>
                                            )}
                                        </button>
                                    </div>
                                    <br />
                                    <p style={{ fontSize: '1rem', margin: '0.5rem 0'}}>
                                        <strong>Title:</strong> {resource.title}
                                    </p>
                                    <p style={{ fontSize: '1rem', margin: '0.5rem 0'}}>
                                        <strong>Link: </strong> 
                                        <a 
                                            href={resource.link} 
                                            target="_blank" 
                                            rel="noopener noreferrer" 
                                            style={{ color: '#3855A7', textDecoration: 'none' }}
                                        >
                                            {resource.link}
                                        </a>
                                    </p>
                                </p>
                            </div>
                        </div>
                    );
                });
            });
        } else {
            return <p>No resources available</p>;
        }
    };
    

    const renderStudyPlan = (plan) => {
        console.log(typeof plan);
        if (!plan || typeof plan !== 'object' || Array.isArray(plan)) {
            console.error('Invalid plan passed to renderStudyPlan:', plan);
            return <p>No valid study plan available.</p>;
        }
        return Object.keys(plan).map((week, weekIndex) => (
            <div key={week} style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '1rem', marginBottom: '1rem', backgroundColor: '#f9f9f9' }}>
                <div
                    style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}
                    onClick={() => handleToggleWeek(week)}
                >
                    <FontAwesomeIcon
                        icon={weekVisibility[week] ? faCaretDown : faCaretRight}
                        style={{ marginRight: '0.5rem' }}
                    />
                    <h3 style={{ borderBottom: '2px solid #ddd', paddingBottom: '0.5rem' }}>{week}</h3>
                </div>
                {weekVisibility[week] && plan[week].map((entry, index) => (
                    <div key={index} style={{ marginBottom: '1rem' }}>
                        <div
                            style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem', cursor: 'pointer' }}
                            onClick={() => handleToggleDay(week, entry.day, entry.topic)}
                        >
                            <FontAwesomeIcon
                                icon={dayVisibility[week]?.[index] ? faCaretDown : faCaretRight}
                                style={{ marginRight: '0.5rem' }}
                            />
                            
                            <p style={{ 
                                fontSize: '1.1rem', 
                                fontWeight: 'bold', 
                                margin: 0, 
                                textDecoration: completedItems[week]?.[index] ? 'line-through' : 'none',
                                color: completedItems[week]?.[index] ? '#aaa' : '#000' 
                            }}>
                                {entry.day}: {entry.topic} 
                            </p>
                            <p style={{
                                marginLeft: '1rem',  
                                fontSize: '1rem',  
                                color: '#888'
                            }}>
                                within {entry.Time}
                            </p>
                        </div>
                        {/* Place toggle message here */}
                        {dayVisibility[week]?.[entry.day] && (
                            <div style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
                                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                                        {explanationContent[week]?.[entry.day] || "Loading explanation..."}
                                    </ReactMarkdown>
                            </div>
                        )}
                        <div style={{ marginLeft: '1rem' }}>
                            <div>
                                {renderResources(entry.resources, entry.topic, weekIndex, index)}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        ));
    };

    if (parsedJson === null) {
        return (
            <div style={{ padding: '1rem', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{markdownText}</ReactMarkdown>
            </div>
        );
    }

    return (
        <div>
            <h2>Study Plan Overview </h2>
            <Editable formData={formData} setResponsePlan={setParsedJson}  setStudyPlan={handleUpdateStudyPlan} participantsId={participantsId}/>
            {parsedJson.studyPlan_Overview && Object.keys(parsedJson.studyPlan_Overview).map(week => (
                <div key={week} style={{ marginBottom: '1rem' }}>
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        cursor: 'pointer',
                        userSelect: 'none'  // Prevents text selection while clicking
                    }}
                    onClick={() => handleToggleWeek(week)}
                >
                    <FontAwesomeIcon
                        icon={weekVisibility[week] ? faCaretDown : faCaretRight}
                        style={{ marginRight: '0.5rem' }}
                    />
                    <h3 style={{ margin: '0 1rem 0 0' }}>{week}:</h3>
                    <p style={{ margin: 0 }}>{parsedJson.studyPlan_Overview[week]}</p>
                </div>
                {weekVisibility[week] && (
                    <div style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
                        {/* Content to be toggled */}
                        <FAQIconStudyPlan week={week} participantsId={participantsId}/>
                    </div>
                    )}
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
                                    <div style={{ 
                                        fontSize: '1rem', 
                                        fontWeight: 'bold', 
                                        textAlign: 'center',
                                        marginRight: '0.5rem'
                                    }}>
                                        {index + 1}.
                                    </div>
                                    <img src={result.thumbnail} alt={result.title} style={{ width: '120px', height: '90px', marginRight: '1rem' }} />
                                    <div>
                                        <p style={{ 
                                            fontSize: '1rem', 
                                            margin: '0'
                                        }}></p>
                                            
                                            <FontAwesomeIcon icon={faThumbsUp} style={{ marginRight: '0.5rem' }} />
                                            {formatNumber(result.likes)}
                                            <span style={{ margin: '0 0.5rem' }}>|</span>
                                            <FontAwesomeIcon icon={faEye} style={{ marginRight: '0.5rem' }} />
                                            {formatNumber(result.views)}
                                            <br></br>
                                        <a href={result.url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>
                                            {result.title}
                                        </a>
                                        <p>{result.description}</p>
                                    </div>
                                    <div style={{ 
                                        display: 'flex', 
                                        justifyContent: 'flex-end', 
                                        alignItems: 'center', 
                                        flex: '0 0 auto', 
                                        marginLeft: 'auto' 
                                    }}>
                                    <button
                                        onClick={() => {
                                            console.log('Selected video index:', index);
                                            handleSelectVideo(selectedWeekIndex, selectedDayIndex, result);
                                        }} 
                                        style={{ 
                                            fontSize: '1rem', 
                                            backgroundColor: '#C0C4C2', 
                                            color: 'white', 
                                            border: 'none', 
                                            borderRadius: '4px', 
                                            cursor: 'pointer', 
                                            
                                        }}>
                                        Select
                                    </button>
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