import { useGetInfoQuery } from "../store/api/infoApi";

export function SafetyBoundaryPanel() {
  const { data } = useGetInfoQuery();

  if (!data) {
    return null;
  }

  return (
    <div className="safety-boundary">
      <div className="safety-boundary-header">
        <svg
          className="safety-boundary-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        <span className="safety-boundary-label">
          {data.readonly ? "Read-only access" : "Read-write access"}
        </span>
      </div>
      {data.allowed_namespaces.length > 0 ? (
        <div className="safety-boundary-ns">
          {data.allowed_namespaces.map((ns) => (
            <span key={ns} className="safety-ns-chip">
              {ns}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
