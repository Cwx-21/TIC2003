function SearchBar({ placeholder, search, setSearch }) {
	return (
		<div className="card">
			<input
				type="text"
				placeholder={placeholder}
				className="search-input"
				value={search}
				onChange={(e) => setSearch(e.target.value)}
			/>
		</div>
	);
}

export default SearchBar;