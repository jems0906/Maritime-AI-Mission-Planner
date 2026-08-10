interface ImportMetaEnv {
	readonly VITE_API_BASE_URL?: string;
	readonly VITE_OPERATOR_API_KEY?: string;
	readonly VITE_REVIEWER_API_KEY?: string;
	readonly VITE_ADMIN_API_KEY?: string;
	readonly DEV?: boolean;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
