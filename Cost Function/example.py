def dx (x, y): return 8*x - 2*y
def dy (x, y): return 4*y - 2*x
def f (x, y): return 4*(x**2) + 2*(y**2) - 2*x*y

def gradient_descent_2():
    # Create gradient arrays
    grad_x = [] 
    grad_y = []
    grad_z = []
    # Our initinal guess
    theta_0  = 25
    theta_1  = 35

    alpha = .05
    epoch = 10000

    grad_x.append(theta_0)
    grad_y.append(theta_1)
    grad_z.append(f(theta_0, theta_1))

    # Run the gradient
    for i in range(epoch):
        current_theta_0 = theta_0 - alpha * dx(theta_0, theta_1)
        current_theta_1 = theta_1 - alpha * dy(theta_0, theta_1)
        grad_x.append(current_theta_0)
        grad_y.append(current_theta_1)
        grad_z.append(f(current_theta_0, current_theta_1))

        # Update
        theta_0 = current_theta_0
        theta_1 = current_theta_1
    
    # Return last values
    return theta_0, theta_1

print(gradient_descent_2())