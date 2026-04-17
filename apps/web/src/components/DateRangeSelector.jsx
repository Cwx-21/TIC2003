function DateRangeSelector({
  startDate,
  endDate,
  setStartDate,
  setEndDate,
  datePreset,
  handleDatePresetChange,
}) {
  return (
    <div className="select-controls">
      <select
        className="select"
        value={datePreset}
        onChange={(event) => handleDatePresetChange(event.target.value)}
      >
        <option value="all">All Time</option>
        <option value="5y">5 Years</option>
        <option value="1y">1 Year</option>
        <option value="1m">1 Month</option>
      </select>

      <div>
        <label className="date-label">Start Date</label>
        <input
          type="date"
          className="select"
          value={startDate}
          onChange={(event) => setStartDate(event.target.value)}
        />
      </div>

      <div>
        <label className="date-label">End Date</label>
        <input
          className="select"
          type="date"
          value={endDate}
          onChange={(event) => setEndDate(event.target.value)}
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
