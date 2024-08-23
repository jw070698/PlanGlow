export const replaceVideoInStudyPlan = (studyPlan, week, dayIndex, selectedVideo) => {
    if (!studyPlan[week] || !Array.isArray(studyPlan[week]) || !studyPlan[week][dayIndex]) {
        console.error('Invalid study plan structure:', studyPlan, week, dayIndex);
        return studyPlan;
    }
    const updatedPlan = {...studyPlan };

    if (!updatedPlan[week][dayIndex].resources) {
        updatedPlan[week][dayIndex].resources = {};
    }

    updatedPlan[week][dayIndex].resources.YouTube = {
        link: selectedVideo.url,
        title: selectedVideo.title,
        thumbnail: selectedVideo.thumbnail,
        views: selectedVideo.views,
        likes: selectedVideo.likes,
    };

    return updatedPlan;
};