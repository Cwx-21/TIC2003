function SentimentTable({ selectedAsset, comments, error }) {
	if (!selectedAsset) {
		return null;
	}

	const displayedComments = comments.filter((item) => item.url);

	return (
		<div className="container">
			<h2>Comments and Sentiment</h2>

			{error && <p>{error}</p>}

			{!error && displayedComments.length === 0 && <p>No comments found.</p>}

			{displayedComments.length > 0 && (
				<div className="sentiment-table-wrapper">
					<table className="sentiment-table">
						<thead>
							<tr>
								<th>Content</th>
								<th>Sentiment Score</th>
							</tr>
						</thead>

						<tbody>
                            {displayedComments.map((item) => (
                                <tr key={item.id}>
                                    <td>
                                        {item.url ? (<a href={item.url} target="_blank" rel="noreferrer" className="comment-link"> {item.content} </a>) : (item.content)}
                                    </td>
                                    <td>{item.sentiment_score}</td>
                                </tr>
                            ))}
                        </tbody>
					</table>
				</div>
			)}
		</div>
	);
}

export default SentimentTable;