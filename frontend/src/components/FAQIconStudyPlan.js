import React, { useEffect, useState, useRef, useCallback } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:1350';

const FAQIconStudyPlan = ({ week, sessionId }) => {
  const [explanationContent, setExplanationContent] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fetchedWeeksRef = useRef({});

  useEffect(() => {
    console.log(`useEffect triggered for week: ${week}`);
    console.log("Current explanationContent:", explanationContent);
    console.log("Current fetchedWeeksRef:", fetchedWeeksRef.current);

    // Check if the explanation for the week has already been fetched
    if (fetchedWeeksRef.current[week] || explanationContent[week]) {
      console.log(`SKIP API CALL for week: ${week}`);
      return;
    }

    const fetchExplanation = async () => {
      try {
        setLoading(true);
        console.log(`Fetching explanation for week: ${week}`);

        // Fetch the explanation from the API
        const response = await axios.post(`${API_BASE_URL}/plan-reasoning`, {
          info_message: "You have suggested a study plan of a sequence of topics. Please give explanations of why you divided the topics this way. \
          Start directly with the explanation of each week, using bullet points.",
          custom_id: sessionId
        });

        const data = response.data.response;
        const splitData = splitExplanationsByWeek(data);

        const updatedContent = {
          ...explanationContent,
          [week]: splitData[week] || 'No explanation available for this week.'
        };

        setExplanationContent(updatedContent);
        fetchedWeeksRef.current[week] = true; // Mark this week as fetched in the ref

        console.log("Updated explanationContent AFTER:", updatedContent);
        console.log("Updated fetchedWeeksRef AFTER:", fetchedWeeksRef.current);

        setLoading(false);
      } catch (error) {
        console.error('API Error:', error);
        setError('Error fetching data from the server.');
        setLoading(false);

        const updatedContent = {
          ...explanationContent,
          [week]: 'Error fetching information for this week. Please try again later.'
        };

        setExplanationContent(updatedContent);
        fetchedWeeksRef.current[week] = true; // Mark this week as fetched even on error to avoid retrying

        console.log("Updated explanationContent", updatedContent);
        console.log("Updated fetchedWeeksRef", fetchedWeeksRef.current);
      }
    };

    fetchExplanation();
  }, [week]);


  const splitExplanationsByWeek = (data) => {
    const splitData = {};
    const weekPattern = /Week\s+(\d+):/g;
    let match;

    while ((match = weekPattern.exec(data)) !== null) {
      const weekNum = `Week ${match[1]}`;
      const start = match.index;
      const end = weekPattern.lastIndex;
      const nextMatch = weekPattern.exec(data);
      const explanation = nextMatch ? data.slice(start, nextMatch.index).trim() : data.slice(start).trim();
      splitData[weekNum] = explanation;
      weekPattern.lastIndex = end;
    }

    return splitData;
  };

  return (
    <div>
      {!loading && explanationContent[week] ? (
        <div style={{ marginTop: '1rem' }}>
          <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
            {explanationContent[week]}
          </ReactMarkdown>
        </div>
      ) : loading ? (
        <p>Loading...</p>
      ) : error ? (
        <p>{error}</p>
      ) : (
        <p>No explanation available for this week.</p>
      )}
    </div>
  );
};

export default FAQIconStudyPlan;