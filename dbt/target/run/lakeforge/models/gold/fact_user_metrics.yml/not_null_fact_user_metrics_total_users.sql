
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_users
from "lakeforge"."main"."fact_user_metrics"
where total_users is null



  
  
      
    ) dbt_internal_test