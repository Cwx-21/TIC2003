function SectionCardStock({ title, items, onItemClick }) {
	return (
		<div className="card">
			<div className="card-title">{title}</div>

			{items.map((item, index) => (
				<div
					key={index}
					className="list-item"
					onClick={() => onItemClick(item.name)}
				>
					{item.name}
				</div>
			))}
		</div>
	);
}

export default SectionCardStock;