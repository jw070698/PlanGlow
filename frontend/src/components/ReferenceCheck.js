import axios from 'axios';
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:1350';


// YouTube 
export const checkAvailability = async(url, participantsId, research_query) => {
    try {
        const response = await axios.post(`${API_BASE_URL}/checkResource`, {
            check_message: url,
            participantsId: participantsId,
            research_query: research_query
        });

        const result = response.data.response;
        if (result.title) {
            return {
                exists: true,
                videoId: result.videoId,
                title: result.title,
                description: result.description,
                thumbnails: result.thumbnails,
                channelTitle: result.channelTitle,
                publishTime: result.publishTime || 'No Publish Time',
            };
        } else {
                return { exists: false, message: result.message };
        }
    } catch (error) {
        console.error("Error checking resource availability:", error);
        return { exists: false, message: "Error occurred during the check" };
    }
};