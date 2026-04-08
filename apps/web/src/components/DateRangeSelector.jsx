function DateRangeSelector({ startDate, endDate, setStartDate, setEndDate }) {
  return (
    <div className="header">
      <div>
        <p>Start Date</p>
        <input
          className="select"
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
        />
      </div>

      <div>
        <p>End Date</p>
        <input
          className="select"
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
        />
      </div>
      <div style={{ marginTop: "18px" }}>
        <button
          className="btn-primary"
          onClick={() => {
            setStartDate("");
            setEndDate("");
          }}
        >
          Clear
        </button>
      </div>
    </div>
  );
}

export default DateRangeSelector;
