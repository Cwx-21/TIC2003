function filterCorrelationData(correlationData, startDate, endDate) {
	return correlationData.filter((item) => {
		const itemDay = item.time_bucket.slice(0, 10);

		const afterStart = startDate ? itemDay >= startDate : true;
		const beforeEnd = endDate ? itemDay <= endDate : true;

		return afterStart && beforeEnd;
	});
}

export default filterCorrelationData;