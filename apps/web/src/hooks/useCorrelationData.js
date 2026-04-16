import { useEffect, useState } from "react";
import api from "../utils/api";

// Fetch correlation data when asset or mode changes
function useCorrelationData(selectedAsset, mode, backtestId, sessionId) {
    const [correlationData, setCorrelationData] = useState([]);
    const [loading, setLoading] = useState(false);
	const [error, setError] = useState("");

    useEffect(() => {
        if (!selectedAsset || !selectedAsset.trim()) {
			setCorrelationData([]);
			setError("");
			return;
        }
        
        if (mode === "backtest" && !backtestId) return;
        if (mode === "live" && !sessionId) return;

        const controller = new AbortController();

        const params =
        mode === "backtest"
            ? `?backtest_id=${backtestId}&interval=1d`
            : `?session_id=${sessionId}`;

        Promise.resolve()
            .then(() => {
                setError("");
                setLoading(true);
                setCorrelationData([]);
                return api.get(`/correlation/${selectedAsset}${params}`, {
                signal: controller.signal,
                });
            })
            .then((res) => setCorrelationData(res.data.data || []))
            .catch((err) => {
                if (err.name !== "CanceledError" && err.code !== "ERR_CANCELED") {
                setError("Failed to load chart data");
                }
            })
            .finally(() => setLoading(false));

        return () => controller.abort();
    }, [selectedAsset, mode, backtestId, sessionId]);

	return { correlationData, loading, error };
}

export default useCorrelationData;