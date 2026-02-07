## Product Requirements Document (PRD)

**Description:** This PRD updates the original specification to focus on integrating X bookmark fetching and management into an existing React-based web application. The existing app already supports bookmarking blog posts and articles, with features for summaries. 

The integration will add seamless support for X bookmarks, allowing users to authenticate with X, fetch their bookmarks, consolidate them with existing (external) bookmarks, and generate unified AI summaries. This enhances the app by providing a centralized dashboard for all bookmarks, including those from X. Built as a modular addition to the existing JS/TS React project, using X's pay-as-you-go API (Basic tier minimum).  

**Target Audience:** Existing users of the app who also use X for bookmarking content, seeking a unified view across sources.  

**Goals:**  

- Extend the existing app with X bookmark integration without disrupting core functionality.  
- Enable fetching and display of X bookmarks alongside blog/article bookmarks.  
- Provide unified AI summaries across all bookmark sources.  

**Assumptions:**  

- The existing app is a React (JS/TS) project with user authentication, bookmark storage (e.g., database or local state), and AI summary generation already implemented.  
- External bookmarks (blog posts/articles) are stored in a normalized format (e.g., with fields like title, url, content, date).  
- AI summarization uses a third-party API (e.g., OpenAI) – integration will leverage the existing setup.  
- The app is deployed as a single-page app (SPA); integration will be added as new components/routes.  

**Scope:** Focus on MVP integration: X auth, fetching, consolidation, and unified dashboard/summaries. Excludes major refactors to existing code unless necessary for compatibility.  

**Tech Stack (Additions/Integrations):**  
- Frontend: Integrate into the existing setup and follow the existing styling and design aesthetic

- Libraries: Add `react-oauth2-code-pkce` (if not present) for X auth, `axios` for API calls, `react-query` for data fetching/caching.  

- State: Integrate with existing state management. 

- Testing: Extend existing tests with Jest + React Testing Library.  

- Deployment: No changes; add new env vars for X API keys.

## Functional Requirements

1. **X User Authentication Integration**  
   - **Req ID:** AUTH-02 (Updated)  
   - **Description:** Add OAuth 2.0 authentication with X to the existing app's auth flow. This allows users to link their X account for bookmark access.  
   - **Instructions to Build:**  
     - Register X Developer App at developer.x.com: Obtain client_id, set redirect_uri to an existing or new callback route in the app (e.g., /x-callback). Enable OAuth 2.0 with scopes: `bookmark.read, users.read, tweet.read, offline.access`.  

     - In Existing App: Add a "Connect X" button in the user profile or settings page. On click, generate code_verifier (random string), compute code_challenge (base64url(SHA256(code_verifier))), and redirect to X auth URL. 

     - Callback Route: Create or extend /x-callback to parse code from URL, POST to X token endpoint (`https://api.twitter.com/2/oauth2/token`) with axios. Store X-specific tokens (access_token, refresh_token) in existing user storage (e.g., localStorage, backend DB, or user context) – associate with the user's app account.  

     - Token Management: Integrate refresh logic into existing auth handlers (e.g., intercept 401 errors to refresh X token).  

     - TS Types: Extend existing User interface with X fields (e.g., `x_user_id: string; x_access_token: string;`).  

     - Edge Cases: Handle if user already connected (check for stored token); prompt re-auth on errors; add disconnect option (revoke via POST /2/oauth2/revoke).  

   - **Acceptance Criteria:** Users can connect/disconnect X; tokens are securely stored and used for API calls.

2. **Fetch X Bookmarks**  
   - **Req ID:** FETCH-01 (Unchanged, Integrated)  

   - **Description:** Retrieve user's X bookmarks and integrate into the existing bookmark fetching pipeline.  

   - **Instructions to Build:**  

     - Trigger: On dashboard load or refresh (if X connected), first fetch user ID via GET /2/users/me using X Bearer token.  
     - Then, call GET /2/users/:id/bookmarks with params (max_results=100, tweet.fields=created_at,text,entities&expansions=author_id).  
     - Pagination: Use react-query's `useInfiniteQuery` (add library if needed) for handling large lists; integrate with existing infinite scroll if present.  
     - Storage: Map X tweets to existing bookmark format (e.g., `{ source: 'X'; title: tweet.text.substring(0,50); url: `https://x.com/${author.username}/status/${tweet.id}`; content: tweet.text; date: new Date(tweet.created_at); }`). Store in existing bookmark state/array.  
     - Error Handling: If not connected, show "Connect X" prompt; handle rate limits with retries/backoff.  

   - **Acceptance Criteria:** X bookmarks appear in the dashboard; fetched only for connected users.

3. **Consolidate Bookmarks**  
   - **Req ID:** CONS-02 (Updated)  

   - **Description:** Merge X bookmarks with existing external (blog/article) bookmarks in the unified dashboard.  

   - **Instructions to Build:**  

     - In Existing Bookmark Reducer/State: Update merge logic to include X source; sort all bookmarks by date descending (or existing sort criteria).  
     - Normalization: Ensure X bookmarks fit existing schema; add optional fields like author for X-specific display.  
     - Import/Upload: If existing app has upload for externals, extend to optionally trigger X fetch on import.  
     - Conflict Handling: Deduplicate by URL if possible (e.g., if an article is bookmarked via X link).  

   - **Acceptance Criteria:** Dashboard shows mixed sources seamlessly; filters (if existing) work across all. Summaries are generated for X Bookmarks the same they do for the regular bookmarks. 

4. **Unified AI Summary Generation**  

   - **Req ID:** AI-02 (Updated)  

   - **Description:** Extend existing AI summary feature to include X bookmarks in the input data for consolidated insights.  

   - **Instructions to Build:**  
     - Trigger: Auto-generated summary that processes X Bookmarks along with existing bookmarks. Since X Bookmarks, are fetch unlike the general bookmarks which are added on user-action, the processing also happens on the background. 
     - Prompt Update: Modify existing AI prompt to handle mixed sources (e.g., "Summarize these bookmarks by themes, noting sources: [X: text1, External: text2]"). Send to existing AI API endpoint.  
     - Display: Render unified summary in existing UI; optionally highlight X-specific themes.  
     - Optimization: If existing batching exists, apply to mixed data; add source tags in output for clarity.  
     - TS: Update async summary function to pull from consolidated bookmarks.  

   - **Acceptance Criteria:** Summaries incorporate X content; no separation unless user filters.

5. **Dashboard UI Enhancements**  
   - **Req ID:** UI-02 (Updated)  
   - **Description:** Update existing app to support X bookmarks with minimal UI changes.  
   - **Instructions to Build:**  
     - Components: Extend existing Bookmark page to handle X source (e.g., show author username, embed tweet if using react-twitter-embed).  
     - Views: Add filter/tab for "X Only" if not present; ensure search/sort works across sources.  
     - Settings Integration: Add X connect status in user profile.  
     - Responsiveness: Match existing styling; no major redesign.  
   - **Acceptance Criteria:** UI remains consistent; X bookmarks display correctly without breaking existing views.

## Non-Functional Requirements

- **Performance:** Cache X API calls with react-query (integrate with existing caching if any); fetch X bookmarks on-demand to avoid overload.  

- **Security:** Store X tokens securely (e.g., encrypted in existing storage); ensure X auth doesn't expose existing app credentials.  

- **Accessibility:** Maintain existing standards; add ARIA for new elements.  

- **Logging/Monitoring:** Extend existing logs to include X API errors.  

- **Testing:** Add tests for new auth flow, fetch, and consolidation; ensure e2e covers integrated scenarios.  

- **Backward Compatibility:** Integration should not break existing external bookmark features.

## Roadmap & Risks

- **Integration Timeline:** 1-2 weeks (auth: 3 days, fetch/consolidate: 4 days, AI/UI: 3 days, testing: 2 days).  

- **Additional Enhancements:** 
- Auto-sync X bookmarks every 12 hours for every user. 
- Export mixed bookmarks - X post links should be present for X bookmarks when expored. 
- Notifications for new X bookmarks (if X webhooks available).  

- **Risks:** 
 - Conflicts with existing auth/state (mitigate with modular code)
 - X API rate limits (add user notifications)
 - privacy concerns (update app's policy to mention X data handling). 

This updated PRD focuses on modular integration to minimize disruption. Start by adding the X auth flow to your existing codebase. If your app uses a backend, consider proxying API calls there for added security.

This PRD provides a blueprint; adapt based on your needs. Start with auth setup in a new React app via `npx create-react-app my-app --template typescript`.


### 1. Endpoints to Use

To fetch the bookmarked posts for an authenticated user via the X API (v2), you'll primarily need the following endpoints. These are part of the X API v2, which supports the pay-as-you-go model (specifically the Basic tier at $100/month, which includes access to bookmark endpoints). Note that the Free tier does not support bookmark lookups, so you'll need at least Basic access. All endpoints require OAuth 2.0 authentication with user context (i.e., an access token obtained via user login).

- **GET /2/users/:id/bookmarks**  
  This is the core endpoint to retrieve a list of posts (tweets) bookmarked by the specified user. Replace `:id` with the user's X user ID (a numeric string).  
  - Key Parameters:  
    - `max_results`: Integer (1-1000, default 100) – Limits the number of bookmarks returned per page.  
    - `pagination_token`: String – For paginating through results (returned in the response meta).  
    - Expansions: e.g., `expansions=attachments.media_keys,author_id` – To include additional data like media, user details, or referenced tweets.  
    - Tweet fields: e.g., `tweet.fields=created_at,text,entities` – To customize the tweet data returned.  
  - Response: JSON object with `data` (array of tweet objects), `includes` (expanded objects like users/media), and `meta` (pagination info).  
  - Rate Limit: 50 requests/15 minutes per user (in Basic tier).  
  - Notes: Only the authenticated user can access their own bookmarks (you can't fetch others'). Use pagination for large bookmark lists.

- **GET /2/users/me**  
  This endpoint retrieves the authenticated user's profile details, including their user ID, which you'll need for the bookmarks endpoint above.  
  - Key Parameters:  
    - `user.fields`: e.g., `user.fields=id,username` – To get specific fields like ID.  
  - Response: JSON with user object (e.g., `{ "data": { "id": "1234567890", "username": "example" } }`).  
  - Rate Limit: 75 requests/15 minutes per app.  
  - Notes: Useful as a starting point after authentication to get the user's ID without hardcoding it.

Other potentially useful endpoints for enhancements:  
- **GET /2/tweets** (with `ids` parameter): If you need to fetch full details for specific tweet IDs from bookmarks.  
- Avoid v1.1 endpoints, as they're deprecated; stick to v2 for pay-as-you-go compatibility.

You'll need an X Developer App registered in the X Developer Portal (developer.x.com) with OAuth 2.0 enabled. Set the app type to "Web App, Automated App or Bot" for user authentication. Ensure your app has read permissions for bookmarks.

### 2. Recommended Flow

The flow involves OAuth 2.0 authentication (using Authorization Code Flow with PKCE for security in a client-side React app), fetching the user's ID, retrieving bookmarks, and then processing them for your dashboard and AI summary. Since this is a React (JS/TS) project, handle API calls in the frontend, but consider a proxy backend (e.g., Node.js/Express) if you need to hide sensitive data like client secrets—though PKCE allows pure client-side.

#### High-Level Flow:
1. **User Authentication (OAuth 2.0)**:  
   - Redirect the user to X's authorization URL: `https://twitter.com/i/oauth2/authorize` (note: still uses twitter.com domain).  
     Parameters: `response_type=code`, `client_id=YOUR_CLIENT_ID`, `redirect_uri=YOUR_APP_URI`, `scope=bookmark.read users.read tweet.read offline.access` (scopes for reading bookmarks, user info, and tweets; `offline.access` for refresh tokens).  
     Use PKCE: Generate a code challenge (SHA-256 hash of a code verifier) and include `code_challenge` and `code_challenge_method=S256`.  
   - User logs in on X and authorizes your app.  
   - X redirects back to your `redirect_uri` with a `code` query param.  
   - Exchange the code for tokens: POST to `https://api.twitter.com/2/oauth2/token` with `grant_type=authorization_code`, `code`, `redirect_uri`, `client_id`, `code_verifier`.  
     Response: `{ access_token, refresh_token, expires_in }`. Store securely (e.g., in localStorage or HttpOnly cookies).  
   - Handle token refresh: When access_token expires, POST to the same token endpoint with `grant_type=refresh_token` and `refresh_token`.

2. **Fetch User ID**:  
   - After getting access_token, call GET /2/users/me with Authorization header: `Bearer YOUR_ACCESS_TOKEN`.  
   - Extract `data.id` from response.

3. **Fetch Bookmarks**:  
   - Call GET /2/users/:id/bookmarks with Bearer token.  
   - Use `max_results` for batching and loop with `pagination_token` until all bookmarks are fetched (handle in a recursive or looped async function).  
   - Parse response: Extract tweet data from `data`, and use `includes` for media/users.

4. **Process Data for Dashboard/AI Summary**:  
   - Consolidate with external bookmarks (assuming you have APIs/sources for those—e.g., browser extensions or other services).  
   - For AI summary: Send bookmark texts to an AI API (e.g., OpenAI/Groq) for summarization/clustering (e.g., group by topics).  
   - Render in React: Use components for dashboard (e.g., list/grid of cards with tweet embeds, summaries).  
   - Error Handling: Handle rate limits (retry with backoff), token expiration (refresh), and auth errors (re-login prompt).  
   - Security: Never expose client_secret in frontend; PKCE avoids it. Use HTTPS.

5. **Logout/Revoke**: Provide a way to revoke access via POST /2/oauth2/revoke.

Implement this in React with libraries like `react-oauth2-code-pkce` for auth flow, `axios` for API calls, and state management (e.g., Redux/Context) for tokens/bookmarks.



Rate Limits: 

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.x.com/llms.txt
> Use this file to discover all available pages before exploring further.

# X API Rate Limits

> Per-endpoint rate limits for X API v2

Rate limits control the number of requests you can make to each endpoint. Exceeding limits results in a 429 error until the window resets.

***

## How rate limits work

| Concept             | Description                                    |
| :------------------ | :--------------------------------------------- |
| **Time window**     | Usually 15 minutes or 24 hours                 |
| **Per-user limits** | Apply with OAuth 1.0a or OAuth 2.0 user tokens |
| **Per-app limits**  | Apply with Bearer Token (app-only)             |
| **Per-endpoint**    | Each endpoint has its own limits               |

***

## Checking your limits

Response headers show your current rate limit status:

```
x-rate-limit-limit: 900
x-rate-limit-remaining: 847
x-rate-limit-reset: 1705420800
```

| Header                   | Description                       |
| :----------------------- | :-------------------------------- |
| `x-rate-limit-limit`     | Maximum requests allowed          |
| `x-rate-limit-remaining` | Requests remaining in window      |
| `x-rate-limit-reset`     | Unix timestamp when window resets |

***

## Rate limit tables

View the rate limit for each endpoint below. You can also see these limits in the [Developer Console](https://console.x.com).

<Note>
  Limits are shown per 15 minutes unless otherwise noted (e.g., "/24hrs" or "/sec").
</Note>

### Posts (25 endpoints)

#### Tweets lookup

| Method | Endpoint        | Per App     | Per User    |
| :----- | :-------------- | :---------- | :---------- |
| GET    | `/2/tweets`     | 3,500/15min | 5,000/15min |
| GET    | `/2/tweets/:id` | 450/15min   | 900/15min   |

#### Recent search

| Method | Endpoint                  | Per App   | Per User  | Notes                                         |
| :----- | :------------------------ | :-------- | :-------- | :-------------------------------------------- |
| GET    | `/2/tweets/search/recent` | 450/15min | 300/15min | 10 default, 100 max results; 512 query length |

#### Full-archive search

| Method | Endpoint               | Per App          | Per User | Notes                                          |
| :----- | :--------------------- | :--------------- | :------- | :--------------------------------------------- |
| GET    | `/2/tweets/search/all` | 1/sec, 300/15min | 1/sec    | 10 default, 500 max results; 1024 query length |

#### Post counts

| Method | Endpoint                  | Per App   | Per User | Notes             |
| :----- | :------------------------ | :-------- | :------- | :---------------- |
| GET    | `/2/tweets/counts/recent` | 300/15min | —        | 512 query length  |
| GET    | `/2/tweets/counts/all`    | 300/15min | —        | 1024 query length |

#### Filtered stream

| Method | Endpoint                        | Per App   | Per User | Notes                                                     |
| :----- | :------------------------------ | :-------- | :------- | :-------------------------------------------------------- |
| GET    | `/2/tweets/search/stream`       | 50/15min  | —        | 1 connection; 1000 rules; 1024 rule length; 250 posts/sec |
| GET    | `/2/tweets/search/stream/rules` | 450/15min | —        | 1 connection; 1000 rules; 1024 rule length                |
| POST   | `/2/tweets/search/stream/rules` | 100/15min | —        | 1 connection; 1000 rules; 1024 rule length                |

#### Manage posts

| Method | Endpoint        | Per App      | Per User  |
| :----- | :-------------- | :----------- | :-------- |
| POST   | `/2/tweets`     | 10,000/24hrs | 100/15min |
| DELETE | `/2/tweets/:id` | —            | 50/15min  |

#### Timelines

| Method | Endpoint                                       | Per App      | Per User  |
| :----- | :--------------------------------------------- | :----------- | :-------- |
| GET    | `/2/users/:id/tweets`                          | 10,000/15min | 900/15min |
| GET    | `/2/users/:id/mentions`                        | 450/15min    | 300/15min |
| GET    | `/2/users/:id/timelines/reverse_chronological` | —            | 180/15min |

#### Likes lookup

| Method | Endpoint                     | Per App  | Per User |
| :----- | :--------------------------- | :------- | :------- |
| GET    | `/2/tweets/:id/liking_users` | 75/15min | 75/15min |
| GET    | `/2/users/:id/liked_tweets`  | 75/15min | 75/15min |

#### Manage likes

| Method | Endpoint                       | Per App | Per User              |
| :----- | :----------------------------- | :------ | :-------------------- |
| POST   | `/2/users/:id/likes`           | —       | 50/15min, 1,000/24hrs |
| DELETE | `/2/users/:id/likes/:tweet_id` | —       | 50/15min, 1,000/24hrs |

#### Retweets lookup

| Method | Endpoint                     | Per App  | Per User | Notes           |
| :----- | :--------------------------- | :------- | :------- | :-------------- |
| GET    | `/2/tweets/:id/retweeted_by` | 75/15min | 75/15min | —               |
| GET    | `/2/tweets/:id/quote_tweets` | 75/15min | 75/15min | —               |
| GET    | `/2/users/reposts_of_me`     | —        | 75/15min | 100 max results |

#### Manage retweets

| Method | Endpoint                          | Per App | Per User |
| :----- | :-------------------------------- | :------ | :------- |
| POST   | `/2/users/:id/retweets`           | —       | 50/15min |
| DELETE | `/2/users/:id/retweets/:tweet_id` | —       | 50/15min |

#### Hide replies

| Method | Endpoint                     | Per App | Per User |
| :----- | :--------------------------- | :------ | :------- |
| PUT    | `/2/tweets/:tweet_id/hidden` | —       | 50/15min |

***

### Users (14 endpoints)

#### Users lookup

| Method | Endpoint                         | Per App   | Per User  |
| :----- | :------------------------------- | :-------- | :-------- |
| GET    | `/2/users`                       | 300/15min | 900/15min |
| GET    | `/2/users/:id`                   | 300/15min | 900/15min |
| GET    | `/2/users/by`                    | 300/15min | 900/15min |
| GET    | `/2/users/by/username/:username` | 300/15min | 900/15min |
| GET    | `/2/users/me`                    | —         | 75/15min  |

#### Search users

| Method | Endpoint          | Per App   | Per User  |
| :----- | :---------------- | :-------- | :-------- |
| GET    | `/2/users/search` | 300/15min | 900/15min |

#### Follows lookup

| Method | Endpoint                 | Per App   | Per User  |
| :----- | :----------------------- | :-------- | :-------- |
| GET    | `/2/users/:id/following` | 300/15min | 300/15min |
| GET    | `/2/users/:id/followers` | 300/15min | 300/15min |

#### Manage follows

| Method | Endpoint                                             | Per App | Per User |
| :----- | :--------------------------------------------------- | :------ | :------- |
| POST   | `/2/users/:id/following`                             | —       | 50/15min |
| DELETE | `/2/users/:source_user_id/following/:target_user_id` | —       | 50/15min |

#### Blocks lookup

| Method | Endpoint                | Per App | Per User |
| :----- | :---------------------- | :------ | :------- |
| GET    | `/2/users/:id/blocking` | —       | 15/15min |

#### Mutes lookup

| Method | Endpoint              | Per App | Per User |
| :----- | :-------------------- | :------ | :------- |
| GET    | `/2/users/:id/muting` | —       | 15/15min |

#### Manage mutes

| Method | Endpoint                                          | Per App | Per User |
| :----- | :------------------------------------------------ | :------ | :------- |
| POST   | `/2/users/:id/muting`                             | —       | 50/15min |
| DELETE | `/2/users/:source_user_id/muting/:target_user_id` | —       | 50/15min |

***

### Spaces (6 endpoints)

#### Spaces lookup

| Method | Endpoint                   | Per App          | Per User         |
| :----- | :------------------------- | :--------------- | :--------------- |
| GET    | `/2/spaces/:id`            | 300/15min        | 300/15min        |
| GET    | `/2/spaces`                | 300/15min        | 300/15min        |
| GET    | `/2/spaces/:id/tweets`     | 300/15min        | 300/15min        |
| GET    | `/2/spaces/by/creator_ids` | 300/15min, 1/sec | 300/15min, 1/sec |
| GET    | `/2/spaces/:id/buyers`     | 300/15min        | 300/15min        |

#### Search Spaces

| Method | Endpoint           | Per App   | Per User  |
| :----- | :----------------- | :-------- | :-------- |
| GET    | `/2/spaces/search` | 300/15min | 300/15min |

***

### Direct Messages (8 endpoints)

#### Direct Messages lookup

| Method | Endpoint                                             | Per App | Per User |
| :----- | :--------------------------------------------------- | :------ | :------- |
| GET    | `/2/dm_events`                                       | —       | 15/15min |
| GET    | `/2/dm_events/:id`                                   | —       | 15/15min |
| GET    | `/2/dm_conversations/:dm_conversation_id/dm_events`  | —       | 15/15min |
| GET    | `/2/dm_conversations/with/:participant_id/dm_events` | —       | 15/15min |

#### Manage Direct Messages

| Method | Endpoint                                            | Per App     | Per User               |
| :----- | :-------------------------------------------------- | :---------- | :--------------------- |
| POST   | `/2/dm_conversations`                               | 1,440/24hrs | 15/15min, 1,440/24hrs  |
| POST   | `/2/dm_conversations/with/:participant_id/messages` | 1,440/24hrs | 15/15min, 1,440/24hrs  |
| POST   | `/2/dm_conversations/:dm_conversation_id/messages`  | 1,440/24hrs | 15/15min, 1,440/24hrs  |
| DELETE | `/2/dm_events/:id`                                  | 4,000/24hrs | 300/15min, 1,500/24hrs |

***

### Lists (14 endpoints)

#### Lists lookup

| Method | Endpoint                   | Per App  | Per User |
| :----- | :------------------------- | :------- | :------- |
| GET    | `/2/lists/:id`             | 75/15min | 75/15min |
| GET    | `/2/users/:id/owned_lists` | 15/15min | 15/15min |

#### List Tweets lookup

| Method | Endpoint              | Per App   | Per User  |
| :----- | :-------------------- | :-------- | :-------- |
| GET    | `/2/lists/:id/tweets` | 900/15min | 900/15min |

#### List member lookup

| Method | Endpoint                        | Per App   | Per User  |
| :----- | :------------------------------ | :-------- | :-------- |
| GET    | `/2/lists/:id/members`          | 900/15min | 900/15min |
| GET    | `/2/users/:id/list_memberships` | 75/15min  | 75/15min  |

#### Manage Lists

| Method | Endpoint       | Per App | Per User  |
| :----- | :------------- | :------ | :-------- |
| POST   | `/2/lists`     | —       | 300/15min |
| DELETE | `/2/lists/:id` | —       | 300/15min |
| PUT    | `/2/lists/:id` | —       | 300/15min |

#### Manage List members

| Method | Endpoint                        | Per App | Per User  |
| :----- | :------------------------------ | :------ | :-------- |
| POST   | `/2/lists/:id/members`          | —       | 300/15min |
| DELETE | `/2/lists/:id/members/:user_id` | —       | 300/15min |

#### Manage List follows

| Method | Endpoint                               | Per App | Per User |
| :----- | :------------------------------------- | :------ | :------- |
| POST   | `/2/users/:id/followed_lists`          | —       | 50/15min |
| DELETE | `/2/users/:id/followed_lists/:list_id` | —       | 50/15min |

#### Pinned Lists

| Method | Endpoint                             | Per App  | Per User |
| :----- | :----------------------------------- | :------- | :------- |
| GET    | `/2/users/:id/pinned_lists`          | 15/15min | 15/15min |
| POST   | `/2/users/:id/pinned_lists`          | —        | 50/15min |
| DELETE | `/2/users/:id/pinned_lists/:list_id` | —        | 50/15min |

***

### Bookmarks (5 endpoints)

#### Bookmarks lookup

| Method | Endpoint                                    | Per App  | Per User  |
| :----- | :------------------------------------------ | :------- | :-------- |
| GET    | `/2/users/:id/bookmarks`                    | —        | 180/15min |
| GET    | `/2/users/:id/bookmarks/folders`            | 50/15min | 50/15min  |
| GET    | `/2/users/:id/bookmarks/folders/:folder_id` | 50/15min | 50/15min  |

#### Manage Bookmarks

| Method | Endpoint                           | Per App | Per User |
| :----- | :--------------------------------- | :------ | :------- |
| POST   | `/2/users/:id/bookmarks`           | —       | 50/15min |
| DELETE | `/2/users/:id/bookmarks/:tweet_id` | —       | 50/15min |

***

### Compliance (3 endpoints)

#### Batch compliance

| Method | Endpoint                     | Per App   | Per User |
| :----- | :--------------------------- | :-------- | :------- |
| POST   | `/2/compliance/jobs`         | 150/15min | —        |
| GET    | `/2/compliance/jobs/:job_id` | 150/15min | —        |
| GET    | `/2/compliance/jobs`         | 150/15min | —        |

***

### Usage (1 endpoint)

| Method | Endpoint          | Per App  | Per User |
| :----- | :---------------- | :------- | :------- |
| GET    | `/2/usage/tweets` | 50/15min | —        |

***

### Trends (2 endpoints)

#### Personalized Trends

| Method | Endpoint                       | Per App              | Per User            |
| :----- | :----------------------------- | :------------------- | :------------------ |
| GET    | `/2/users/personalized_trends` | 200/24hrs, 200/15min | 100/24hrs, 10/15min |

#### Trends by WOEID

| Method | Endpoint                 | Per App  | Per User |
| :----- | :----------------------- | :------- | :------- |
| GET    | `/2/trends/by/woeid/:id` | 75/15min | —        |

***

### Communities (2 endpoints)

| Method | Endpoint                | Per App   | Per User  | Notes           |
| :----- | :---------------------- | :-------- | :-------- | :-------------- |
| GET    | `/2/communities/:id`    | 300/15min | 300/15min | —               |
| GET    | `/2/communities/search` | 300/15min | 300/15min | 100 max results |

***

### Analytics (1 endpoint)

| Method | Endpoint              | Per App   | Per User  |
| :----- | :-------------------- | :-------- | :-------- |
| GET    | `/2/tweets/analytics` | 300/15min | 300/15min |

***

### Media (8 endpoints)

| Method | Endpoint                       | Per App       | Per User    |
| :----- | :----------------------------- | :------------ | :---------- |
| POST   | `/2/media/upload`              | 50,000/24hrs  | 500/15min   |
| GET    | `/2/media/upload`              | 100,000/24hrs | 1,000/15min |
| POST   | `/2/media/upload/initialize`   | 180,000/24hrs | 1,875/15min |
| POST   | `/2/media/upload/:id/append`   | 180,000/24hrs | 1,875/15min |
| POST   | `/2/media/upload/:id/finalize` | 180,000/24hrs | 1,875/15min |
| POST   | `/2/media/metadata`            | 50,000/24hrs  | 500/15min   |
| POST   | `/2/media/subtitles`           | 10,000/24hrs  | 100/15min   |
| DELETE | `/2/media/subtitles`           | 10,000/24hrs  | 100/15min   |

***

### Activity & Webhooks

| Method | Endpoint                                     | Per App   | Per User | Notes                        |
| :----- | :------------------------------------------- | :-------- | :------- | :--------------------------- |
| GET    | `/2/activity/stream`                         | 450/15min | —        | 2 connections; 250 posts/sec |
| POST   | `/2/activity/subscriptions`                  | 500/15min | —        | —                            |
| GET    | `/2/activity/subscriptions`                  | 500/15min | —        | —                            |
| PUT    | `/2/activity/subscriptions/:subscription_id` | 500/15min | —        | —                            |
| DELETE | `/2/activity/subscriptions/:subscription_id` | 500/15min | —        | —                            |
| POST   | `/2/webhooks`                                | 450/15min | —        | —                            |
| GET    | `/2/webhooks`                                | 450/15min | —        | —                            |
| PUT    | `/2/webhooks/:webhook_id`                    | 450/15min | —        | —                            |
| DELETE | `/2/webhooks/:webhook_id`                    | 450/15min | —        | —                            |
| POST   | `/2/webhooks/replay`                         | 100/15min | —        | —                            |

***

### Other endpoints

| Method | Endpoint                                  | Per App               | Per User            |
| :----- | :---------------------------------------- | :-------------------- | :------------------ |
| GET    | `/2/tweets/sample10/stream`               | 100/15min             | —                   |
| GET    | `/2/news/:id`                             | 200/15min             | —                   |
| GET    | `/2/news/search`                          | 200/15min             | 200/15min           |
| POST   | `/2/users/:id/dm/block`                   | 25/15min, 1,000/24hrs | 10/15min, 400/24hrs |
| POST   | `/2/users/:id/dm/unblock`                 | 25/15min, 1,000/24hrs | 10/15min, 400/24hrs |
| GET    | `/2/users/by/username/:username/tweets`   | 1,500/15min           | 900/15min           |
| GET    | `/2/users/by/username/:username/mentions` | 450/15min             | 180/15min           |
| GET    | `/2/users/:id/following/spaces`           | 300/15min             | 300/15min           |
| GET    | `/2/tweets/:id/retweets`                  | 75/15min              | 75/15min            |
| DELETE | `/2/connections/all`                      | 25/15min              | 25/15min            |

***

## Handling rate limits

When you hit a rate limit, you'll receive a 429 response:

```json  theme={null}
{
  "errors": [{
    "code": 88,
    "message": "Rate limit exceeded"
  }]
}
```

### Recovery strategy

1. Check `x-rate-limit-reset` for when the window resets
2. Wait until that time before retrying
3. Use exponential backoff if needed

```python  theme={null}
import time

def make_request_with_backoff(url, headers):
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        reset_time = int(response.headers.get('x-rate-limit-reset', 0))
        wait_time = max(reset_time - time.time(), 60)
        time.sleep(wait_time)
        return make_request_with_backoff(url, headers)
    
    return response
```

***

## Best practices

<CardGroup cols={2}>
  <Card title="Cache responses" icon="database">
    Store results locally to reduce repeated requests.
  </Card>

  <Card title="Use streaming" icon="signal-stream">
    For real-time data, use filtered stream instead of polling.
  </Card>

  <Card title="Monitor headers" icon="gauge-high">
    Track remaining requests to avoid hitting limits.
  </Card>

  <Card title="Spread requests" icon="clock">
    Distribute requests across the time window.
  </Card>
</CardGroup>

***

## Rate limits vs. billing

Rate limits and billing are separate:

| Concept           | Purpose                                        |
| :---------------- | :--------------------------------------------- |
| **Rate limits**   | Control request frequency for system stability |
| **Usage billing** | Charge for data retrieved (pay-per-usage)      |

You can be within rate limits but still incur usage costs, or hit rate limits without additional cost.

***

## Enterprise rate limits

Enterprise customers have custom rate limits. Contact your account manager or [apply for Enterprise access](/enterprise/forms/enterprise-api-interest).

***

## Next steps

<CardGroup cols={2}>
  <Card title="Error handling" icon="triangle-exclamation" href="/x-api/fundamentals/response-codes-and-errors">
    Handle 429 and other errors.
  </Card>

  <Card title="Getting started" icon="rocket" href="/x-api/getting-started/about-x-api">
    Learn about access levels and features.
  </Card>
</CardGroup>
