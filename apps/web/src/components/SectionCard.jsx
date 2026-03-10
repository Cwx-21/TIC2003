function SectionCard({ title, items, onItemClick }) {

    return (
        <div className="card">
            <div className="cart-title">{title}</div>

            {items.map((item, index) => (
                <div
                    key={index}
                    className="list-item"
                    onClick={() => onItemClick(item)}
                >
                    {item}
                </div>
            ))}
        </div>
    )
}

export default SectionCard;