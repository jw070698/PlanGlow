export const replaceVideoInStudyPlan = (studyPlan, week, dayIndex, selectedVideo) => {
    if (!studyPlan[week] || !Array.isArray(studyPlan[week]) || !studyPlan[week][dayIndex]) {
        console.error('Invalid study plan structure:', studyPlan, week, dayIndex);
        return studyPlan;
    }
    const updatedPlan = {...studyPlan };

    if (!updatedPlan[week][dayIndex].resources) {
        updatedPlan[week][dayIndex].resources = { YouTube: [] };
    } else if (!Array.isArray(updatedPlan[week][dayIndex].resources.YouTube)) {
        updatedPlan[week][dayIndex].resources.YouTube = [];
    }

    // Ensure the specified video index exists
    if (videoIndex >= 0 && videoIndex < updatedPlan[week][dayIndex].resources.YouTube.length) {
        // Replace the specific video at the given index
        updatedPlan[week][dayIndex].resources.YouTube[videoIndex] = {
            link: selectedVideo.url,
            title: selectedVideo.title,
            thumbnail: selectedVideo.thumbnail,
            views: selectedVideo.views,
            likes: selectedVideo.likes,
        };
    } else {
        console.error('Invalid video index:', videoIndex);
    }


    return updatedPlan;
};