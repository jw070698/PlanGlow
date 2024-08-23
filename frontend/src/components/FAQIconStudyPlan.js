import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

const API_BASE_URL = "http://localhost:1350";

const FAQIconStudyPlan = ({ week }) => {
  const [explanationContent, setExplanationContent] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchExplanation = async () => {
      try {
        // Check if the explanation for the week already exists
        if (explanationContent[week]) {
          console.log(`Explanation for ${week} is already fetched.`);
          return; // If it exists, skip the API call
        }

        setLoading(true);

        // Fetch the explanation from the API
        const response = await axios.post(`${API_BASE_URL}/plan-reasoning`, {
          info_message: "You have suggested a study plan of a sequence of topics. Please give explanations of why you divided the topics this way. Start directly with the explanation of each week, using bullet points."
        });

        const data = response.data.response;

        // Split the content into weeks
        const splitData = splitExplanationsByWeek(data);
        // Save the fetched content in the state
        setExplanationContent(prevState => ({
          ...prevState,
          [week]: splitData[week] || 'No explanation available for this week.'
        }));

        setLoading(false);
      } catch (error) {
        console.error('API Error:', error);
        setError('Error fetching data from the server.');
        setLoading(false);
        setExplanationContent(prevState => ({
          ...prevState,
          [week]: 'Error fetching information for this week. Please try again later.'
        }));
      }
    };

    fetchExplanation();
  }, [week, explanationContent]);

  const splitExplanationsByWeek = (data) => {
    const splitData = {};
    const weekPattern = /Week\s+(\d+):/g;
    let match;

    while ((match = weekPattern.exec(data)) !== null) {
      const weekNum = `Week ${match[1]}`;
      const start = match.index;
      console.log(start);
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
      {loading ? (
        <p>Loading...</p>
      ) : error ? (
        <p>{error}</p>
      ) : explanationContent[week] ? (
        <div style={{ marginTop: '1rem' }}>
          <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
            {explanationContent[week]}
          </ReactMarkdown>
        </div>
      ) : (
        <p>No explanation available for this week.</p>
      )}
    </div>
  );
};

export default FAQIconStudyPlan;
