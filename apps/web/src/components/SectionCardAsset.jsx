function SectionCardAsset({ title, items, onItemClick }) {
  return (
    <div>
      <div className='container'>
        <div className='header'>
          <h2>{title}</h2>
        </div>
        <div className="card-list">
          {items.map((item, index) => (
            <div
              key={index}
              className='card'
              onClick={() => onItemClick(item.symbol)}
            >
              {item.name} ({item.symbol})
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SectionCardAsset;