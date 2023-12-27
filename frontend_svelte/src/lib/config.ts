import dotenv from 'dotenv';
dotenv.config();

import { ManagedIdentityCredential } from "@azure/identity";
import { SecretClient } from "@azure/keyvault-secrets";


export const app_config = async () => {
	const configuration = {
		backend_host: process.env.BACKEND_HOST,
		app_reg_client_id : process.env.APP_REG_CLIENT_ID,
		authority: process.env.AUTHORITY,
	}
	if (process.env.AZURE_KEYVAULT_HOST) {
		const credential = new ManagedIdentityCredential();
		const client = new SecretClient(process.env.AZURE_KEYVAULT_HOST, credential);
		const secretName = 'keyvault-health';
		const keyvaultHealth = await client.getSecret(secretName);
		return { 
			status: keyvaultHealth,
			backend_host: process.env.BACKEND_HOST,
		 }; // TBD: change into actually retrieving KEYVAULT_HEALTH from KEYVAULT_HOST
	}
	return { status: process.env.KEYVAULT_HEALTH };
};
