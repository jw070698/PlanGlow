import axios from 'axios';
const API_BASE_URL = "https://ai-curriculum-pi.vercel.app";


// YouTube 
export const checkAvailability = async(url, custom_id) => {
    try {
        const response = await axios.post(`${API_BASE_URL}/checkResource`, {
            check_message: url,
            custom_id: custom_id
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

// Blog
export const checkAvailabilityBlog = async(url) => {
    try {
        console.log(url)
        const response = await axios.post(`${API_BASE_URL}/checkResource`, {
            check_message: url
        });
        const result = response.data.response;
        console.log(result.title)
        if (result.title) {
            console.log(`Video found: ${result.title}`);
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