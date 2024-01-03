import { PublicClientApplication, type AccountInfo, InteractionRequiredAuthError } from '@azure/msal-browser';
import { get } from 'svelte/store';
import { microsoft_account_store } from './stores';
// import { microsoft_account_store } from './stores';
// import { auth_instance_store } from './stores';
// import { error } from '@sveltejs/kit';
// import { auth_instance_store } from './stores';
// import { app_config } from '$lib/config';


// const configuration =  await app_config()

// try {
//   const azure_authority = configuration.azure_authority;
//   const app_reg_client_id = configuration.app_reg_client_id;
//   return { authority: azure_authority, client_id: app_reg_client_id };
// }
//   catch (err) {
//     console.error(err);
//     throw error(404, 'App configuration unavailable');
//   }



export class Authentication {
  msalInstance: PublicClientApplication


  constructor(clientId: string, authority: string) {
    const msalConfig = {
      auth: {
        clientId: clientId,
        authority: authority, 
      },
    }
    this.msalInstance = new PublicClientApplication(msalConfig);
  }
  
  async initialize() {
    await this.msalInstance.initialize();
    await this.msalInstance.handleRedirectPromise();
    console.log("oauth - msalInstance initialized");
    return this.msalInstance;
  }
    
  async signIn(redirectOrigin: string) {
    // if (msalInstance !== undefined) {
      // if ( this.msalInstance?.getInProgress) {
      //   console.log('Interaction in progress, retrieving active account');
      //   await this.msalInstance?.getActiveAccount().setInteractionInProgress(false);
      // }
      try {
        await this.msalInstance.handleRedirectPromise();
        this.msalInstance.loginRedirect({
        // scopes: ["read.all"],// TBD: fix scopes to the ones registered in app registration
        // scopes: [`api://${configuration.api_scope}`],
        scopes: [],
        redirectUri: `${redirectOrigin}/oauth/callback`
      }); // add scopes here?
      const response = await this.msalInstance.handleRedirectPromise();
      return response;
    } catch (err) {
      // if ( error instanceof BrowserAuthError) {
      //   // console.log('Interaction in progress, retrieving active account');
      //   await initialMsalInstance.getActiveAccount().setInteractionInProgress(false);
      // } else {
      // console.error(err);
      console.error("oauth - Login failed: ", err);
      throw err
      // }
    }
  // }
}

async getAccount(): Promise<AccountInfo> {
  try {
    await this.msalInstance.handleRedirectPromise();
    const accounts = this.msalInstance.getAllAccounts();
    console.log("oauth - GetAccount - accounts");
    console.log(accounts);
    return accounts[0];
  } catch (err) {
    console.error("oauth - GetAccount failed: ", err);
    throw err
  }

}

async getAccessToken( scopes: string[] = []) {
  try {
    await this.msalInstance.handleRedirectPromise();
    const account = await this.getAccount();
    const tokenRequest = {
      scopes: scopes,
      account: account,
    }
    try{
      const response = await this.msalInstance.acquireTokenSilent(tokenRequest);
      console.log("oauth - GetAccessToken - response");
      console.log(response);
      return response.accessToken;
      } catch (error) {
        if( error instanceof InteractionRequiredAuthError) {
          // EventMessageUtils.getInteractionStatusFromEvent(TBD: find correct EventMessage here)
          // await this.msalInstance.getInteractionStatusFromEvent() 
          // if (myGlobalState.getInteractionStatus() !== InteractionStatus.None) {
          //   // throw a new error to be handled in the caller below
          //   throw new Error("interaction_in_progress");
          const tokenRequestNew = {
            ...tokenRequest,
            redirectUri: `${window.location.origin}/oauth/callback`,
          }
          await this.msalInstance.acquireTokenRedirect(tokenRequestNew)
        } else {
          console.error("oauth - GetAccessToken failed - no AuthError: ", error);
          throw error;
        }
      }
  } catch (err) {
    console.error("oauth - GetAccessToken failed: ", err);
    throw err
  }

}

async signOut(redirectOrigin: string, redirectUri: string = "/") {
  try {
    await this.msalInstance.handleRedirectPromise();
    // console.log("oauth - signout - redirectUri");
    // console.log(`${redirectOrigin}${redirectUri}`);
    // const accounts = this.msalInstance.getAllAccounts();
    await this.msalInstance.logoutRedirect({
      postLogoutRedirectUri: `${redirectOrigin}${redirectUri}`
    });
  } catch (err) {
    console.error("oauth - Logout failed: ", err);
    throw err// error(404, 'Logout failed')
  }
  }
}

export const getAccessToken = async () => {
  const microsoftAccountStore = get(microsoft_account_store);
  const tenant = microsoftAccountStore?.[0]?.tenantId;

}

export default Authentication;
// export const createAuthentication = () =>  {
//   const authInstance = new Authentication(configuration.app_reg_client_id, configuration.azure_authority)
//   console.log('auth created a new authInstance')
//   auth_instance_store.set(authInstance);
// }


// const msalConfig = {
//   auth: {
//     clientId: configuration.app_reg_client_id,
//     authority: configuration.azure_authority, 
//   },
// }

// export const signIn = async (app_reg_client_id: string, azure_authority: string, host: string) => {
//   const msalConfig = {
//     auth: {
//       clientId: app_reg_client_id,
//       authority: azure_authority,
//       redirectUri: `${host}/oauth/callback`,
//     },
//     // cacheOptions: {
//     //   storeAuthStateInCookie: true,
//     //   secureCookies: true
//     // }
//   };
//   // console.log("oauth - signin - msalConfig");
//   // console.log(msalConfig);

//   const initialMsalInstance = await new PublicClientApplication(msalConfig);
//   await initialMsalInstance.initialize();

//   // sessionStorage.setItem("msal.initialMsalInstance", JSON.stringify(initialMsalInstance));
//   // console.log("oauth - signin - initialMsalInstance");
//   // console.log(initialMsalInstance);

//   //TBD: put msalInstance in Svelte store and use the one from the store in the rest of the application!
//   // const msalInstanceStore = writable(initialMsalInstance)
//   // msalInstanceStore.set(initialMsalInstance);
//   // let msalInstance = get( msalInstanceStore );
//   // const msalInstance = get( msalInstanceStore );

//   // const redirectUri = `${host}/oauth/callback`;
//   try {
//     // const redirectUri = `${host}/oauth/callback`;
//     initialMsalInstance.loginRedirect({ 
//       // scopes: ["read.all"],// TBD: fix scopes to the ones registered in app registration
//       // scopes: [`api://${configuration.api_scope}`],
//       scopes: [],
//       // redirectUri: redirectUri
//     }); // add scopes here?
//     const response = await initialMsalInstance.handleRedirectPromise();
//     sessionStorage.setItem("msal.responseLoginRedirect", JSON.stringify(response));
//     console.log("oauth - signin - response");
//     console.log(response);
//     console.log("oauth - signin - response?.idToken");
//     console.log(response?.idToken);
//     return response;
//   } catch (err) {
//     // if ( error instanceof BrowserAuthError) {
//     //   // console.log('Interaction in progress, retrieving active account');
//     //   await initialMsalInstance.getActiveAccount().setInteractionInProgress(false);
//     // } else {
//     // console.error(err);
//     throw err
//     // }
//   }
// };

// // not perfectly working yet - uses another msalinstance to logout!
// export const signOut = async (app_reg_client_id: string, azure_authority: string, host: string) => {
//   console.log("oauth - signout");
//   const msalConfig = {
//     auth: {
//       clientId: app_reg_client_id,
//       authority: azure_authority,
//       redirectUri: `${host}/oauth/callback`,
//     },
//   }
//   const msalInstance = new PublicClientApplication(msalConfig);
//   await msalInstance.initialize();
//   console.log("oauth - signout - msalInstance");
//   console.log(msalInstance);
//   msalInstance.logoutRedirect()
//   // const msalInstance = get( msalInstanceStore );
//   // console.log("oauth - signout - msalInstance");
//   // console.log(msalInstance);
//   // await msalInstance?.logoutRedirect();
//   // await msalInstance?.logoutRedirect({
//   //   postLogoutRedirectUri: `${window.location.origin}/`
//   // });
// }