function presetDates(preset, correlationData) {
    if (!correlationData.length) {
		return { start: "", end: "" };
    }
    
    const sortedData = [...correlationData].sort(
      (a, b) => new Date(a.time_bucket) - new Date(b.time_bucket),
    );

    const firstDate = sortedData[0].time_bucket.slice(0, 10);
    const lastDate = sortedData[sortedData.length - 1].time_bucket.slice(0, 10);

    if (preset === "all") {
		return { start: "", end: "" };
    }
    
    const end = new Date(lastDate);
    const start = new Date(lastDate);

    if (preset === "5y") {
        start.setFullYear(start.getFullYear() - 5);
    } else if (preset === "1y") {
        start.setFullYear(start.getFullYear() - 1);
    } else if (preset === "1m") {
        start.setMonth(start.getMonth() - 1);
    }

    const formattedStart = start.toISOString().slice(0, 10);
    const formattedEnd = end.toISOString().slice(0, 10);

    return {
		start: formattedStart < firstDate ? firstDate : formattedStart,
		end: formattedEnd,
	};
}

export default presetDates;