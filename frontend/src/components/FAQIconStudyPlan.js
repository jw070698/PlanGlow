import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:1350';

const FAQIconStudyPlan = ({ week, participantsId }) => {
  const [explanationContent, setExplanationContent] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fetchedWeeksRef = useRef({});

  useEffect(() => {
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
          info_message:
            'You have suggested a study plan of a sequence of topics. Please give explanations of why you divided the topics this way. Start directly with the explanation of each week, using bullet points.',
          participantId: participantsId,
        });

        let data = response.data.response || response.data;
        let explanationByWeek;

        // Check if data is a string that needs parsing
        if (typeof data === 'string') {
          // Clean up the data string to make it valid JSON
          data = preprocessDataString(data);
          // Try to parse the cleaned JSON string
          try {
            data = JSON.parse(data);
          } catch (parseError) {
            console.error('Failed to parse data as JSON after preprocessing:', parseError);
            explanationByWeek = {};
          }
        }
        console.log("data", data)
        if (typeof data === 'object' && data !== null) {
          explanationByWeek = data;
        } else{
          console.log('Data is empty or in an unexpected format.');
          explanationByWeek = {};
        }

        // Normalize keys in explanationByWeek
        const normalizedExplanations = {};
        for (const key in explanationByWeek) {
          const normalizedKey = key.replace(/\s+/g, '').toLowerCase();
          normalizedExplanations[normalizedKey] = explanationByWeek[key];
        }
        console.log('Normalized explanations:', normalizedExplanations);

        // Normalize the week variable
        const normalizedWeek = week.replace(/\s+/g, '').toLowerCase();

        let explanationForWeek =
          normalizedExplanations[normalizedWeek] || 'No explanation available for this week.';
        console.log(`Explanation for ${week}:`, explanationForWeek);

        // Add bullet points before each section heading
        explanationForWeek = explanationForWeek
          .replace(/(Learning objective:)/g, 'Learning objective:')
          .replace(/(Content selection:)/g, '\n - $1')
          .replace(/(Connection:)/g, '\n- $1');

        const updatedContent = {
          ...explanationContent,
          [week]: explanationForWeek,
        };

        setExplanationContent(updatedContent);
        fetchedWeeksRef.current[week] = true; // Mark this week as fetched
        console.log('Updated explanationContent:', updatedContent);
        setLoading(false);
      } catch (error) {
        console.error('API Error:', error);
        setError('Error fetching data from the server.');
        setLoading(false);

        const updatedContent = {
          ...explanationContent,
          [week]: 'Error fetching information for this week. Please try again later.',
        };

        setExplanationContent(updatedContent);
        fetchedWeeksRef.current[week] = true;
      }
    };

    fetchExplanation();
  }, [week]);

  const preprocessDataString = (data) => {
    try {
      // Remove Markdown code block markers and trim whitespace
      data = data.replace(/```json/g, '').replace(/```/g, '').trim();
  
      // Ensure JSON formatting issues are fixed
      data = data.replace(/(\r\n|\n|\r)/gm, ''); // Remove line breaks
      data = data.replace(/,(\s*[}\]])/g, '$1'); // Remove trailing commas
      data = data.replace(/([{,])\s*(\w+)\s*:/g, '$1"$2":'); // Quote keys
      return data;
    } catch (error) {
      console.error('Error preprocessing data string:', error);
      return data;
    }
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
