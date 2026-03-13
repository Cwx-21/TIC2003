function SearchBar({ placeholder , searchTerm, setSearchTerm }) {
    
    return (
        <div className="card">
            <input
                type="text"
                placeholder={placeholder}
                className="search-input"
                value={searchTerm}
			    onChange={(entry) => setSearchTerm(entry.target.value)}
            />
        </div>
    );
}

export default SearchBar;