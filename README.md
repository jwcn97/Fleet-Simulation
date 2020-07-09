# fleet_simulation 

This project simulates and evaluates different charging algorithms for a fleet of vehicles in the depot based on a variety of factors such as:<br/>
1) fleet schedule<br/>
2) number of electric charge points in the depot<br/>
3) maximum charge rate of the depot<br/>
(main file located in folder: ver11)<br/>

<img src="/archive/ver8/results_test/shift1_BG_HighMpkwLowSD_car1_charge.png" /><br/>

The image above shows that the COST algorithm works the best because<br/>
1) the algorithm waits for the low tariff zone (blue area) before charging the vehicle at a cheaper rate<br/>
2) there is no expensive rapid charging needed outside the depot (denoted by the red dots)
