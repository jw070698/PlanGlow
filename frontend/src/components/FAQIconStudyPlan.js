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
    console.log(`useEffect triggered for week: ${week}`);
    console.log('Current explanationContent:', explanationContent);
    console.log('Current fetchedWeeksRef:', fetchedWeeksRef.current);

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

        if (typeof data === 'object' && data !== null) {
          explanationByWeek = data;
        } else if (!explanationByWeek) {
          console.log('Data is empty or in an unexpected format.');
          explanationByWeek = {};
        }

        // Normalize keys in explanationByWeek
        const normalizedExplanations = {};
        for (const key in explanationByWeek) {
          const normalizedKey = key.replace(/\s+/g, '').toLowerCase();
          normalizedExplanations[normalizedKey] = explanationByWeek[key];
        }

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
    // Remove any line breaks within the JSON keys and values
    data = data.replace(/(\r\n|\n|\r)/gm, '');
    // Remove any trailing commas that would make the JSON invalid
    data = data.replace(/,(\s*[}\]])/g, '$1');
    // Ensure keys and string values are properly quoted
    data = data.replace(/([{,])\s*(\w+)\s*:/g, '$1"$2":');
    // Escape double quotes inside string values
    data = data.replace(/:\s*"([\s\S]*?)"/g, (match, p1) => {
      const escapedValue = p1.replace(/"/g, '\\"');
      return `: "${escapedValue}"`;
    });
    return data;
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
