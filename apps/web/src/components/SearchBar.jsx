function SearchBar({ title, placeholder, search, setSearch }) {
  return (
    <div className='container'>
        <div className='header'>
          <h2>{title}</h2>
        </div>
    <input
      type='text'
      placeholder={placeholder}
      className='search-input'
      value={search}
      onChange={(event) => setSearch(event.target.value)}
      />
  </div>
    
  );
}

export default SearchBar;
