function SearchBar({ placeholder, search, setSearch }) {
  return (
    <input
      type='text'
      placeholder={placeholder}
      className='search-input'
      value={search}
      onChange={(e) => setSearch(e.target.value)}
    />
  );
}

export default SearchBar;
