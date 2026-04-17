function SectionCardAsset({ title, items, onItemClick }) {
  return (
    <div>
      <div className="container" data-testid="asset-list">
        <h2>{title}</h2>
        <div className="card-list">
          {items.map((item, index) => (
            <div
              key={index}
              className="card"
              data-testid="asset-card"
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
