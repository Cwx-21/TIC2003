function DateRangeSelector({ startDate, endDate, setStartDate, setEndDate, datePreset, handleDatePresetChange }) {
  return (
    <div className="select-controls">
			<select
				className="select"
				value={datePreset}
				onChange={(entry) => handleDatePresetChange(entry.target.value)}
			>
				<option value="all">All Time</option>
				<option value="5y">5 Years</option>
				<option value="1y">1 Year</option>
				<option value="1m">1 Month</option>
				<option value="1d">1 Day</option>
			</select>

			<div className="date-input-group">
				<label>Start Date</label>
				<input
					type="date"
					value={startDate}
					onChange={(entry) => setStartDate(entry.target.value)}
				/>
			</div>

			<div className="date-input-group">
				<label>End Date</label>
				<input
					type="date"
					value={endDate}
					onChange={(entry) => setEndDate(entry.target.value)}
				/>
			</div>

			<button
				className="btn-primary"
				onClick={() => {
					setStartDate("");
					setEndDate("");
					handleDatePresetChange("all");
				}}
			>
				Clear
			</button>
		</div>
  );
}

export default DateRangeSelector;
