import matplotlib.pyplot as plt

f = open("results.txt", "r")
avg_fitness_list = []
best_fitness_list = []
while True:
    line = f.readline()
    if "Process finished with exit code 137 (interrupted by signal 9: SIGKILL)" in line:
        break
    if "Population's average fitness:" in line:
        avg_fitness = float(line[30:39])
        avg_fitness_list.append(avg_fitness)
    if "Best fitness:" in line:
        best_fitness = float(line[14:23])
        best_fitness_list.append(best_fitness)

fig = plt.figure()
fig.subplots_adjust(top=0.95)
ax1 = fig.add_subplot(1, 1, 1)
ax1.set_ylabel('fitness')
ax1.set_xlabel('generations')
ax1.set_title('fitness of best genome vs current generation')
ax1.plot(avg_fitness_list)
ax1.plot(best_fitness_list)
plt.show()