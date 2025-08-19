Calculate customer LTV for customer from Jan 2023 to Dec 2023 by subscription types (monthly, annual and total combined), 
subscription & plan types (basic, pro and enterprise), 
subscription & customer industry and 
subscription and acquisition channel. 
Create four separate tabs for each type. Total Customer LTV in one, Customer LTV by plan in another tab, customer LTV by Industry in another tab and Customer LTV by Channel in a separate tab.
Use initial subscription and plan type to calculate LTV, not current subscription or plan type, so keep them in the subscription and plan they started in regardless of if they changed to another subscription or plan type. 
To calculate LTV use the formula (LTV = (Average Revenue per User / Churn Rate) × Profit Margin). 
To calculate churn rate, use the formula (# of customers at the beginning of the period / # of churned customers during time period), if a customer has 0% churn assume that they will be a customer for 5 years until they churn in order to calculate LTV and keep that as a  assumption in the model that can be toggled as a driver.Create a separate tab with a CAC to LTV analysis by each acquisition channel. If there is no CAC by subscription type & channel then compare LTV by total CACs by channel.
Profit per User should only include profit generated from Jan 2023 to Dec 2023 from users who ordered during those dates.
Customers at the start of the period should only be customers who have active subscriptions in Jan 2023. 
Churned customers should be customers who were active subscribers between Jan 2023 and Dec 2023 and churned during that period and should not include customers who joined after Jan 2023 since we want the churn rate for customers who were active on Jan 2023 and not new customers who joined after Jan 2023.