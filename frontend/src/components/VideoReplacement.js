export const replaceVideoInStudyPlan = (studyPlan, selectedVideo, week, dayIndex) => {
    const updatedPlan = {...studyPlan };

    if (updatedPlan[week] && updatedPlan[week][dayIndex]) {
        updatedPlan[week][dayIndex].resources.YouTube = {
            title: selectedVideo.title,
            link: selectedVideo.url,
            thumbnail: selectedVideo.thumbnail,
        };
    }

    return updatedPlan;
};