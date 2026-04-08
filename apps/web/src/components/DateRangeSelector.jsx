function DateRangeSelector({ startDate, endDate, setStartDate, setEndDate }) {
  return (
    <div className="date-range">
      <div>
        <p>Start Date</p>
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
        />
      </div>

      <div>
        <p>End Date</p>
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
        />
      </div>

      <button
        onClick={() => {
          setStartDate("");
          setEndDate("");
        }}
      >
        Clear
      </button>
    </div>
  );
}

export default DateRangeSelector;