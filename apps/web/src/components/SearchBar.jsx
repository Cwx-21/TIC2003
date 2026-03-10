function SearchBar({ placeholder }) {

    
    return (
        <div className="card">
            <input
                type="text"
                placeholder={placeholder}
                className="search-input"
            />
        </div>
    );
}

export default SearchBar;