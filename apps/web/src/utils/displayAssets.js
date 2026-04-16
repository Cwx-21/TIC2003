function displayAssets(assets, searchAsset) {
	const filteredAssets = assets.filter((item) => {
		return (
			item.name.toLowerCase().includes(searchAsset.toLowerCase()) ||
			item.symbol.toLowerCase().includes(searchAsset.toLowerCase())
		);
	});

	return searchAsset ? filteredAssets : assets.slice(0, 5);
}

export default displayAssets;