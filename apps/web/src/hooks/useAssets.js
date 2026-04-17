import { useEffect, useState } from "react";
import api from "../utils/api";

//load asset list
function useAssets() {
    const [assets, setAssets] = useState([]);
    const [error, setError] = useState("");

    useEffect(() => {
		api
			.get("/assets")
			.then((res) => {
				setAssets(res.data.data || []);
				setError("");
			})
			.catch(() => {
				setError("Failed to load assets");
				setAssets([]);
			});
	}, []);

	return { assets, error };
}

export default useAssets;