import React, { useState } from 'react';
import axios from 'axios';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCircleQuestion } from '@fortawesome/free-solid-svg-icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import Modal from 'react-modal';

const API_BASE_URL = "https://ai-curriculum-pi.vercel.app";

const FAQIconStudyPlan = () => {
  const [modalIsOpen, setModalIsOpen] = useState(false);
  const [modalContent, setModalContent] = useState('');

  const handlePlanReasoningClick = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/plan-reasoning`, {
        info_message: "You have suggested a study plan of a sequence of topics. Why do you divide the topics in this way?"
      });
      setModalContent(response.data.response); // Store the fetched data in the state
      setModalIsOpen(true); // Open the modal
    } catch (error) {
      console.error('Error fetching info from backend', error);
      setModalContent('Error fetching data from the server.');
      setModalIsOpen(true); // Open the modal even if there's an error, to show the error message
    }
  };

  return (
    <>
      {/* The FAQ icon that will trigger the modal */}
      <FontAwesomeIcon 
        icon={faCircleQuestion} 
        style={{ cursor: 'pointer', color: '#007bff', marginLeft: '10px' }} 
        onClick={handlePlanReasoningClick}
      />
                                    
      {/* Modal to display the fetched content */}
      <Modal
        isOpen={modalIsOpen}
        onRequestClose={() => setModalIsOpen(false)}
        contentLabel="Study Plan Details"
        style={{
          content: {
            top: '50%',
            left: '50%',
            right: 'auto',
            bottom: 'auto',
            marginRight: '-50%',
            transform: 'translate(-50%, -50%)',
            maxWidth: '600px',
            width: '90%',
            borderRadius: '10px',
            padding: '20px',
            maxHeight: '400px', // Limit the height of the modal
            overflowY: 'auto' // Enable scrolling when content exceeds the height
          },
        }}
      >
        <button onClick={() => setModalIsOpen(false)} style={{ float: 'right', backgroundColor: '#007bff', color: 'white', border: 'none', padding: '5px 10px', cursor: 'pointer' }}>Close</button>
        <div style={{ 
          maxHeight: '500px', // Increased content area height
          overflowY: 'auto', 
          fontSize: '18px', // Increased font size for content
          lineHeight: '1.6', // Adjusted line height for readability
          color: '#333' // Darker text color for better readability
        }}>
          <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
            {modalContent}
          </ReactMarkdown>
        </div>
      </Modal>
    </>
  );
};

export default FAQIconStudyPlan;
